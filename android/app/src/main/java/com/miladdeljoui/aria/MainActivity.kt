package com.miladdeljoui.aria

import android.content.Context
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

data class ChatItem(val owner: Boolean, val text: String)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AriaApp()
                }
            }
        }
    }
}

@Composable
fun AriaApp() {
    val context = LocalContext.current
    val prefs = remember {
        context.getSharedPreferences("aria", Context.MODE_PRIVATE)
    }
    val uiHandler = remember { Handler(Looper.getMainLooper()) }

    var serverUrl by remember {
        mutableStateOf(
            prefs.getString("server_url", "http://192.168.1.100:8765") ?: ""
        )
    }
    var pairingCode by remember { mutableStateOf("") }
    var token by remember { mutableStateOf(prefs.getString("token", "") ?: "") }
    var message by remember { mutableStateOf("") }
    var status by remember {
        mutableStateOf(if (token.isBlank()) "Not connected" else "Paired")
    }
    val messages = remember { mutableStateListOf<ChatItem>() }
    val executor = remember { Executors.newSingleThreadExecutor() }

    val tts = remember {
        TextToSpeech(context) {}
    }

    fun updateUi(block: () -> Unit) {
        uiHandler.post(block)
    }

    fun postJson(path: String, body: JSONObject, authToken: String = ""): String {
        val connection = (
            URL(serverUrl.trimEnd('/') + path).openConnection() as HttpURLConnection
        )
        connection.requestMethod = "POST"
        connection.connectTimeout = 5000
        connection.readTimeout = 120000
        connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        if (authToken.isNotBlank()) {
            connection.setRequestProperty("X-ARIA-Token", authToken)
        }

        connection.outputStream.use { stream ->
            stream.write(body.toString().toByteArray(Charsets.UTF_8))
        }

        val responseCode = connection.responseCode
        val stream = if (responseCode in 200..299) {
            connection.inputStream
        } else {
            connection.errorStream
        }

        val response = stream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        connection.disconnect()

        if (responseCode !in 200..299) {
            error("HTTP $responseCode: $response")
        }

        return response
    }

    fun pair() {
        executor.execute {
            try {
                val body = JSONObject()
                    .put("code", pairingCode.trim())
                    .put("device_name", android.os.Build.MODEL)

                val result = JSONObject(postJson("/pair", body))
                val newToken = result.getString("token")

                prefs.edit()
                    .putString("server_url", serverUrl.trimEnd('/'))
                    .putString("token", newToken)
                    .apply()

                updateUi {
                    token = newToken
                    status = "Paired with ARIA"
                }
            } catch (e: Exception) {
                updateUi {
                    status = "Pairing error: " + (e.message ?: "unknown error")
                }
            }
        }
    }

    fun sendMessage() {
        val prompt = message.trim()
        if (prompt.isBlank()) return

        messages.add(ChatItem(owner = true, text = prompt))
        message = ""

        executor.execute {
            try {
                if (token.isBlank()) {
                    updateUi { status = "First pair this phone with ARIA" }
                    return@execute
                }

                val body = JSONObject()
                    .put("prompt", prompt)
                    .put("history", org.json.JSONArray())

                val result = JSONObject(postJson("/chat", body, token))
                val answer = result.getString("answer")

                updateUi {
                    messages.add(ChatItem(owner = false, text = answer))
                    tts.speak(answer, TextToSpeech.QUEUE_FLUSH, null, "aria-answer")
                    status = "Connected"
                }
            } catch (e: Exception) {
                updateUi {
                    status = "Connection error: " + (e.message ?: "unknown error")
                }
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("ARIA", style = MaterialTheme.typography.headlineMedium)
        Text(
            "دستیار شخصی محلی + لپ‌تاپ",
            style = MaterialTheme.typography.bodyMedium
        )

        OutlinedTextField(
            value = serverUrl,
            onValueChange = { serverUrl = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("آدرس لپ‌تاپ") },
            placeholder = { Text("http://192.168.1.100:8765") }
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = pairingCode,
                onValueChange = { pairingCode = it },
                modifier = Modifier.weight(1f),
                label = { Text("کد اتصال") }
            )
            Button(onClick = { pair() }) {
                Text("اتصال")
            }
        }

        Text("وضعیت: $status", style = MaterialTheme.typography.bodySmall)

        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(messages) { item ->
                Text(
                    text = (if (item.owner) "تو: " else "ARIA: ") + item.text,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        Spacer(modifier = Modifier.height(4.dp))

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = message,
                onValueChange = { message = it },
                modifier = Modifier.weight(1f),
                label = { Text("پیام") }
            )
            Button(onClick = { sendMessage() }) {
                Text("ارسال")
            }
        }
    }
}
