package com.miladdeljoui.aria

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

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
        connection.connectTimeout = 8000
        connection.readTimeout = 120000
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
            val errorCode = parsed?.optString("error", "http_error") ?: "http_error"
            val message = parsed?.optString("message")
                ?.takeIf { it.isNotBlank() }
                ?: when (errorCode) {
                    "invalid_pairing_code" ->
                        "کد جفت‌سازی اشتباه است. کد ۶ رقمی ترمینال سرور را وارد کنید."
                    "unauthorized" ->
                        "دستگاه هنوز جفت نشده یا توکن منقضی شده است."
                    "ollama_unavailable" ->
                        "Ollama روی سرور در دسترس نیست."
                    else ->
                        "خطای ارتباط (HTTP $responseCode)"
                }
            throw AriaException(errorCode, message)
        }

        return JSONObject(raw)
    }

    fun pair(
        baseUrl: String,
        code: String,
        deviceName: String
    ): String {
        val cleanCode = code.trim().filter { it.isDigit() }
        if (cleanCode.length != 6) {
            throw AriaException(
                "invalid_pairing_code",
                "کد جفت‌سازی باید دقیقاً ۶ رقم باشد."
            )
        }

        val result = request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/pair",
            body = JSONObject()
                .put("code", cleanCode)
                .put("device_name", deviceName)
        )
        return result.getString("token")
    }

    fun chat(
        baseUrl: String,
        token: String,
        prompt: String
    ): AriaResponse {
        val result = request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/chat",
            body = JSONObject()
                .put("prompt", prompt)
                .put("history", JSONArray()),
            token = token
        )

        val permission = result.optJSONObject("permission")

        return AriaResponse(
            answer = result.optString("answer", "پاسخ دریافت نشد."),
            permissionLevel = permission?.optString("level", "safe") ?: "safe",
            requiresApproval = permission?.optBoolean("requires_approval", false) ?: false
        )
    }

    fun status(baseUrl: String): JSONObject {
        return request(
            method = "GET",
            baseUrl = baseUrl,
            path = "/status"
        )
    }
}
