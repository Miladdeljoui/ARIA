package com.miladdeljoui.aria

import android.content.Context
import android.util.Base64
import androidx.core.content.FileProvider
import org.json.JSONArray
import java.util.UUID
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.io.File

data class AriaResponse(
    val answer: String,
    val permissionLevel: String,
    val requiresApproval: Boolean
)

class AriaApi {

    class AriaException(val errorCode: String, message: String) : Exception(message)

    private fun request(
        method: String,
        baseUrl: String,
        path: String,
        body: JSONObject? = null,
        token: String = ""
    ): JSONObject {
        val connection = (
            URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection
        )

        connection.requestMethod = method
        connection.connectTimeout = 45000
        connection.readTimeout = 240000
        connection.setRequestProperty(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        if (token.isNotBlank()) {
            connection.setRequestProperty("X-ARIA-Token", token)
        }

        if (body != null) {
            connection.doOutput = true
            connection.outputStream.use { output ->
                output.write(body.toString().toByteArray(Charsets.UTF_8))
            }
        }

        val responseCode = connection.responseCode
        val stream = if (responseCode in 200..299) {
            connection.inputStream
        } else {
            connection.errorStream ?: connection.inputStream
        }

        val raw = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: ""
        connection.disconnect()

        if (responseCode !in 200..299) {
            val parsed = runCatching { JSONObject(raw) }.getOrNull()
            val detail = parsed?.optString("detail").orEmpty()
            val errorCode = parsed?.optString("error")?.takeIf { it.isNotBlank() }
                ?: detail.takeIf { it.isNotBlank() }
                ?: "http_error"
            val message = parsed?.optString("message")?.takeIf { it.isNotBlank() }
                ?: parsed?.optString("hint")?.takeIf { it.isNotBlank() }
                ?: when (detail.ifBlank { errorCode }) {
                    "cloud_ai_not_configured" ->
                        "مدل هوش مصنوعی ابری هنوز تنظیم نشده است."
                    "ai_provider_unavailable_or_invalid_response" ->
                        "سرویس هوش مصنوعی پاسخ نداد؛ تنظیمات مدل ابری را بررسی کنید."
                    "unauthorized" ->
                        "دسترسی این دستگاه معتبر نیست. یک بار اتصال خودکار را دوباره امتحان کن."
                    "guest_registration_limit" ->
                        "تعداد اتصال‌های جدید از این شبکه برای امروز زیاد شده است."
                    "daily_guest_chat_limit" ->
                        "سهمیهٔ رایگان امروز این دستگاه تمام شده است."
                    "daily_service_limit" ->
                        "سهمیهٔ رایگان روزانهٔ ARIA تمام شده؛ فردا دوباره امتحان کن."
                    "cloud_ai_not_configured" ->
                        "مدل هوش مصنوعی روی سرور هنوز تنظیم نشده است."
                    "media_generation_disabled_by_server" ->
                        "ساخت تصویر و کلیپ هنوز از طرف سرور فعال نشده است."
                    "image_provider_unavailable_check_model_and_credits" ->
                        "ساخت تصویر ناموفق بود؛ مدل یا اعتبار سرویس را بررسی کن."
                    "video_provider_unavailable_check_model_and_credits" ->
                        "ساخت کلیپ ناموفق بود؛ مدل یا اعتبار سرویس را بررسی کن."
                    else ->
                        "خطای ارتباط (HTTP $responseCode)"
                }
            throw AriaException(errorCode, message)
        }

        return JSONObject(raw)
    }

    fun guest(baseUrl: String, clientId: String, deviceName: String = "ARIA Android"): String {
        val result = request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/guest",
            body = JSONObject()
                .put("client_id", clientId)
                .put("device_name", deviceName)
        )
        return result.getString("token")
    }

    fun generateImage(baseUrl: String, token: String, prompt: String): JSONObject {
        return request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/media/image",
            body = JSONObject().put("prompt", prompt),
            token = token
        )
    }

    fun generateVideo(
        baseUrl: String,
        token: String,
        prompt: String,
        duration: Int = 5,
        aspectRatio: String = "16:9"
    ): JSONObject {
        return request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/media/video",
            body = JSONObject()
                .put("prompt", prompt)
                .put("duration", duration)
                .put("aspect_ratio", aspectRatio),
            token = token
        )
    }

    fun videoStatus(baseUrl: String, token: String, jobId: String): JSONObject {
        return request(
            method = "GET",
            baseUrl = baseUrl,
            path = "/media/video/" + java.net.URLEncoder.encode(jobId, "UTF-8"),
            token = token
        )
    }

    fun chat(
        baseUrl: String,
        token: String,
        prompt: String,
        history: List<Pair<String, String>> = emptyList()
    ): AriaResponse {
        val historyJson = JSONArray()
        history.takeLast(12).forEach { (role, content) ->
            if ((role == "user" || role == "assistant") && content.isNotBlank()) {
                historyJson.put(
                    JSONObject()
                        .put("role", role)
                        .put("content", content.take(12000))
                )
            }
        }
        val result = request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/chat",
            body = JSONObject()
                .put("prompt", prompt)
                .put("history", historyJson),
            token = token
        )

        val permission = result.optJSONObject("permission")

        return AriaResponse(
            answer = result.optString("answer", "پاسخ دریافت نشد."),
            permissionLevel = permission?.optString("level", "safe") ?: "safe",
            requiresApproval = permission?.optBoolean("requires_approval", false) ?: false
        )
    }


    // اتصال مستقیم و بدون حساب به OVHcloud AI Endpoints؛ مناسب آزمایش سبک.
    // محدودیت رسمی ناشناس: ۲ درخواست در دقیقه به‌ازای IP و مدل.
    fun freeProviderStatus(): JSONObject {
        return request(
            method = "GET",
            baseUrl = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
            path = "/models"
        )
    }

    fun freeChat(
        prompt: String,
        history: List<Pair<String, String>> = emptyList()
    ): AriaResponse {
        val messages = JSONArray()
        messages.put(
            JSONObject()
                .put("role", "system")
                .put("content", "تو ARIA هستی، دستیار هوشمند فارسی. پاسخ‌ها را دقیق، کاربردی و به زبان کاربر بده. اگر کاربر فارسی نوشت، فارسی روان پاسخ بده.")
        )
        history.takeLast(12).forEach { (role, content) ->
            if ((role == "user" || role == "assistant") && content.isNotBlank()) {
                messages.put(
                    JSONObject().put("role", role).put("content", content.take(8000))
                )
            }
        }
        messages.put(JSONObject().put("role", "user").put("content", prompt.take(12000)))
        val result = request(
            method = "POST",
            baseUrl = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
            path = "/chat/completions",
            body = JSONObject()
                .put("model", "gpt-oss-20b")
                .put("messages", messages)
                .put("stream", false)
        )
        val choices = result.optJSONArray("choices")
        val answer = choices?.optJSONObject(0)?.optJSONObject("message")
            ?.optString("content").orEmpty().trim()
        if (answer.isBlank()) throw AriaException("empty_ai_response", "مدل هوش مصنوعی پاسخ خالی برگرداند.")
        return AriaResponse(answer, "safe", false)
    }

    private fun pollinationsBytes(url: String, apiKey: String): ByteArray {
        if (apiKey.isBlank()) {
            throw AriaException(
                "pollinations_key_required",
                "برای ساخت عکس یا کلیپ، کلید App Key با پیشوند pk_ را در تنظیمات وارد کن. از کلید محرمانه sk_ داخل اپ استفاده نکن. دریافت کلید: enter.pollinations.ai"
            )
        }
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.requestMethod = "GET"
        connection.connectTimeout = 15000
        connection.readTimeout = 300000
        connection.setRequestProperty("Authorization", "Bearer ${apiKey.trim()}")
        connection.setRequestProperty("Accept", "image/*, video/mp4, application/json")
        val code = connection.responseCode
        if (code !in 200..299) {
            val raw = (connection.errorStream ?: connection.inputStream).bufferedReader(Charsets.UTF_8).use { it.readText() }
            connection.disconnect()
            val message = when (code) {
                401, 403 -> "کلید Pollinations معتبر نیست یا اجازهٔ این مدل را ندارد."
                402 -> "اعتبار Pollinations تمام شده است؛ هزینه و موجودی حساب را بررسی کن."
                429 -> "سهمیهٔ Pollinations موقتاً تمام شده؛ کمی بعد دوباره امتحان کن."
                else -> "سرویس رسانه پاسخ خطا داد (HTTP $code): ${raw.take(180)}"
            }
            throw AriaException("pollinations_http_$code", message)
        }
        val type = connection.contentType.orEmpty()
        if (type.contains("application/json", ignoreCase = true)) {
            val raw = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            connection.disconnect()
            throw AriaException("unexpected_media_response", "سرویس به‌جای فایل رسانه‌ای پاسخ JSON برگرداند: ${raw.take(180)}")
        }
        val bytes = connection.inputStream.use { it.readBytes() }
        connection.disconnect()
        if (bytes.isEmpty()) throw AriaException("empty_media_response", "فایل رسانه‌ای خالی بود.")
        return bytes
    }

    fun generatePollinationsImage(prompt: String, apiKey: String): String {
        val encodedPrompt = URLEncoder.encode(prompt, "UTF-8").replace("+", "%20")
        val bytes = pollinationsBytes(
            "https://gen.pollinations.ai/image/$encodedPrompt?model=flux",
            apiKey
        )
        return Base64.encodeToString(bytes, Base64.NO_WRAP)
    }

    fun generatePollinationsVideo(prompt: String, apiKey: String, context: Context): String {
        val encodedPrompt = URLEncoder.encode(prompt, "UTF-8").replace("+", "%20")
        val bytes = pollinationsBytes(
            "https://gen.pollinations.ai/video/$encodedPrompt?duration=5&aspectRatio=16%3A9",
            apiKey
        )
        val directory = File(context.cacheDir, "aria_media")
        if (!directory.exists() && !directory.mkdirs()) {
            throw AriaException("media_storage_failed", "فضای موقت ذخیرهٔ کلیپ ساخته نشد.")
        }
        val file = File(directory, "aria_video_${System.currentTimeMillis()}.mp4")
        file.writeBytes(bytes)
        return FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file
        ).toString()
    }

    fun status(baseUrl: String): JSONObject {
        return request(
            method = "GET",
            baseUrl = baseUrl,
            path = "/status"
        )
    }

    fun subscription(baseUrl: String, token: String): JSONObject {
        return request(
            method = "GET",
            baseUrl = baseUrl,
            path = "/subscription",
            token = token
        )
    }

    fun sendFeedback(
        baseUrl: String,
        token: String,
        category: String,
        message: String,
        appVersion: String
    ): JSONObject {
        return request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/feedback",
            body = JSONObject()
                .put("category", category)
                .put("message", message)
                .put("app_version", appVersion),
            token = token
        )
    }

    fun latestUpdate(baseUrl: String): JSONObject {
        return request(
            method = "GET",
            baseUrl = baseUrl,
            path = "/updates/latest"
        )
    }

}
