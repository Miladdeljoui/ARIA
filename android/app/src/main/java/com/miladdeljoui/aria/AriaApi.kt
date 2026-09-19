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
        connection.connectTimeout = 5000
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
            connection.errorStream
        }

        val raw = stream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        connection.disconnect()

        if (responseCode !in 200..299) {
            error("HTTP $responseCode: $raw")
        }

        return JSONObject(raw)
    }

    fun pair(
        baseUrl: String,
        code: String,
        deviceName: String
    ): String {
        val result = request(
            method = "POST",
            baseUrl = baseUrl,
            path = "/pair",
            body = JSONObject()
                .put("code", code.trim())
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
