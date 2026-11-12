package com.miladdeljoui.aria

import android.content.Context
import android.util.Base64
import androidx.core.content.FileProvider
import org.json.JSONArray
import java.util.UUID
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
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
        connection.readTimeout = 360000
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
                    "Not Found", "not_found" ->
                        "مسیر این قابلیت روی سرور پیدا نشد؛ احتمالاً نسخهٔ قدیمی ARIA روی دامنه نصب است. پوشهٔ cloud و فایل Dockerfile باید روی همان دامنه Deploy شوند."
                    "subscription_required" ->
                        "دورهٔ آزمایشی این حساب تمام شده است. برای ادامه، اشتراک را از بخش بسته‌ها فعال کن."
                    "payment_not_configured" ->
                        "درگاه هنوز روی سرور فعال نشده است؛ مدیر باید شناسهٔ پذیرنده و دامنهٔ HTTPS را تنظیم کند."
                    "payment_gateway_unavailable" ->
                        "ارتباط با درگاه پرداخت برقرار نشد. هزینه‌ای پرداخت نشده؛ کمی بعد دوباره تلاش کن."
                    "payment_request_rejected" ->
                        "درخواست پرداخت از طرف درگاه پذیرفته نشد. تنظیمات پذیرنده یا حالت آزمایشی را بررسی کن."
                    "ai_provider_not_configured", "hosted_ai_not_configured" ->
                        "کلید یا مدل هوش مصنوعی روی سرور تنظیم نشده است؛ ARIA_API_KEY و نام مدل را در بخش Secret بررسی کن."
                    "cloud_ai_not_configured" ->
                        "مدل هوش مصنوعی ابری هنوز تنظیم نشده است."
                    "ai_provider_unavailable_or_invalid_response" ->
                        "سرویس هوش مصنوعی پاسخ نداد؛ تنظیمات مدل ابری را بررسی کنید."
                    "provider_wallet_empty" ->
                        "اعتبار کیف پول سرویس 1xAi کافی نیست؛ موجودی API را بررسی کن."
                    "provider_profile_incomplete" ->
                        "پروفایل احراز هویت 1xAi تکمیل نشده است؛ از پنل خود سرویس تکمیلش کن."
                    "model_not_allowed" ->
                        "این مدل برای نسخهٔ فعلی ARIA فعال نشده است."
                    "unauthorized" ->
                        "دسترسی این دستگاه معتبر نیست. یک بار اتصال خودکار را دوباره امتحان کن."
                    "guest_registration_limit" ->
                        "تعداد اتصال‌های جدید از این شبکه برای امروز زیاد شده است."
                    "daily_guest_chat_limit" ->
                        "سهمیهٔ رایگان امروز این دستگاه تمام شده است."
                    "daily_paid_chat_limit" ->
                        "سهمیهٔ ۱۰۰ پیام روزانهٔ اشتراک این دستگاه تمام شده است."
                    "daily_service_limit" ->
                        "سهمیهٔ رایگان روزانهٔ ARIA تمام شده؛ فردا دوباره امتحان کن."
                    "daily_image_limit", "daily_service_image_limit" ->
                        "سهمیهٔ ساخت تصویر امروز تمام شده است."
                    "daily_video_limit", "daily_service_video_limit" ->
                        "سهمیهٔ ساخت کلیپ امروز تمام شده است."
                    "cloud_ai_not_configured" ->
                        "مدل هوش مصنوعی روی سرور هنوز تنظیم نشده است."
                    "media_generation_disabled_by_server" ->
                        "ساخت تصویر و کلیپ هنوز از طرف سرور فعال نشده است."
                    "image_provider_not_configured" ->
                        "کلید سرویس ساخت تصویر هنوز در سرور تنظیم نشده است."
                    "video_provider_not_configured" ->
                        "کلید سرویس ساخت کلیپ هنوز در سرور تنظیم نشده است."
                    "video_file_too_large" ->
                        "حجم کلیپ بیشتر از سقف ۲۰ مگابایت است."
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
        history: List<Pair<String, String>> = emptyList(),
        selectedModel: String = ""
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
        val chatBody = JSONObject()
            .put("prompt", prompt)
            .put("history", historyJson)
        if (selectedModel.isNotBlank()) chatBody.put("model", selectedModel)
        val result = request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/chat",
            body = chatBody,
            token = token
        )

        val permission = result.optJSONObject("permission")

        return AriaResponse(
            answer = result.optString("answer", "پاسخ دریافت نشد."),
            permissionLevel = permission?.optString("level", "safe") ?: "safe",
            requiresApproval = permission?.optBoolean("requires_approval", false) ?: false
        )
    }


    fun saveVideoBase64(context: Context, encoded: String): String {
        if (encoded.isBlank()) throw AriaException("empty_video_response", "فایل کلیپ خالی است.")
        val bytes = try {
            Base64.decode(encoded, Base64.DEFAULT)
        } catch (error: IllegalArgumentException) {
            throw AriaException("invalid_video_base64", "فایل کلیپ دریافتی معتبر نیست.")
        }
        if (bytes.isEmpty()) throw AriaException("empty_video_response", "فایل کلیپ خالی است.")
        if (bytes.size > 20 * 1024 * 1024) {
            throw AriaException("video_file_too_large", "حجم کلیپ بیش از سقف ۲۰ مگابایت است.")
        }
        val directory = File(context.cacheDir, "aria_media")
        if (!directory.exists() && !directory.mkdirs()) {
            throw AriaException("media_storage_failed", "فضای موقت ذخیرهٔ کلیپ ساخته نشد.")
        }
        val file = File(directory, "aria_video_${System.currentTimeMillis()}.mp4")
        try {
            file.writeBytes(bytes)
            return FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                file
            ).toString()
        } catch (error: Exception) {
            file.delete()
            throw AriaException("media_storage_failed", "ذخیرهٔ کلیپ روی گوشی ناموفق بود.")
        }
    }

    fun status(baseUrl: String): JSONObject {
        return request(
            method = "GET",
            baseUrl = baseUrl,
            path = "/status"
        )
    }

    fun models(baseUrl: String, token: String): JSONObject {
        return request(
            method = "GET",
            baseUrl = baseUrl,
            path = "/models",
            token = token
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

    fun createPayment(baseUrl: String, token: String): JSONObject {
        return request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/billing/request",
            body = JSONObject(),
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
