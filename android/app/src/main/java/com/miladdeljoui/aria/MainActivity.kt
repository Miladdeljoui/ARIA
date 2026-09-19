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
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import java.util.Locale
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
    val executor = remember { Executors.newSingleThreadExecutor() }
    val api = remember { AriaApi() }

    var cloudUrl by remember {
        mutableStateOf(prefs.getString("cloud_url", "") ?: "")
    }
    var localUrl by remember {
        mutableStateOf(
            prefs.getString("local_url", "http://192.168.0.4:8765") ?: ""
        )
    }
    var cloudToken by remember {
        mutableStateOf(prefs.getString("cloud_token", "") ?: "")
    }
    var localToken by remember {
        mutableStateOf(prefs.getString("local_token", "") ?: "")
    }
    var pairingCode by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("آماده") }

    val messages = remember { mutableStateListOf<ChatItem>() }

    val tts = remember {
        TextToSpeech(context) {}
    }

    fun updateUi(block: () -> Unit) {
        uiHandler.post(block)
    }

    fun pairCloud() {
        if (cloudUrl.isBlank()) {
            status = "آدرس Cloud را وارد کن."
            return
        }

        executor.execute {
            try {
                val token = api.pair(
                    baseUrl = cloudUrl,
                    code = pairingCode,
                    deviceName = "ARIA Android Cloud"
                )

                prefs.edit()
                    .putString("cloud_url", cloudUrl.trimEnd('/'))
                    .putString("cloud_token", token)
                    .apply()

                updateUi {
                    cloudToken = token
                    status = "Cloud متصل شد"
                }
            } catch (e: Exception) {
                updateUi {
                    status = "خطای Cloud: " + (e.message ?: "unknown")
                }
            }
        }
    }

    fun pairLocal() {
        executor.execute {
            try {
                val token = api.pair(
                    baseUrl = localUrl,
                    code = pairingCode,
                    deviceName = "ARIA Android Local"
                )

                prefs.edit()
                    .putString("local_url", localUrl.trimEnd('/'))
                    .putString("local_token", token)
                    .apply()

                updateUi {
                    localToken = token
                    status = "لپ‌تاپ متصل شد"
                }
            } catch (e: Exception) {
                updateUi {
                    status = "خطای لپ‌تاپ: " + (e.message ?: "unknown")
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
                var response: AriaResponse? = null
                var source = ""

                if (cloudToken.isNotBlank() && cloudUrl.isNotBlank()) {
                    try {
                        response = api.chat(cloudUrl, cloudToken, prompt)
                        source = "Cloud"
                    } catch (_: Exception) {
                        // Automatic local fallback.
                    }
                }

                if (response == null && localToken.isNotBlank() && localUrl.isNotBlank()) {
                    response = api.chat(localUrl, localToken, prompt)
                    source = "Laptop"
                }

                if (response == null) {
                    error("هیچ اتصال مجازی به ARIA موجود نیست")
                }

                val result = response ?: error("پاسخ دریافت نشد.")
                val approval = if (result.requiresApproval) {
                    "\n\n🔐 نیازمند تأیید مالک: " + result.permissionLevel
                } else {
                    ""
                }

                updateUi {
                    messages.add(
                        ChatItem(
                            owner = false,
                            text = "[" + source + "] " + result.answer + approval
                        )
                    )
                    tts.language = Locale("fa", "IR")
                    tts.speak(
                        result.answer,
                        TextToSpeech.QUEUE_FLUSH,
                        null,
                        "aria-answer"
                    )
                    status = "متصل از طریق " + source
                }
            } catch (e: Exception) {
                updateUi {
                    messages.add(
                        ChatItem(
                            owner = false,
                            text = "ARIA: خطا در اتصال. " + (e.message ?: "unknown")
                        )
                    )
                    status = "اتصال برقرار نشد"
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
        Text(
            "ARIA",
            style = MaterialTheme.typography.headlineMedium
        )
        Text(
            "Cloud-first + Laptop fallback",
            style = MaterialTheme.typography.bodyMedium
        )

        OutlinedTextField(
            value = cloudUrl,
            onValueChange = { cloudUrl = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("آدرس Cloud") },
            placeholder = { Text("https://aria.example.com") }
        )

        OutlinedTextField(
            value = localUrl,
            onValueChange = { localUrl = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("آدرس لپ‌تاپ") },
            placeholder = { Text("http://192.168.0.4:8765") }
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = pairingCode,
                onValueChange = { pairingCode = it },
                modifier = Modifier.weight(1f),
                label = { Text("کد اتصال") }
            )
            Button(onClick = { pairLocal() }) {
                Text("لپ‌تاپ")
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { pairCloud() }) {
                Text("Cloud")
            }
            OutlinedButton(
                onClick = {
                    status = "Cloud: " +
                        if (cloudToken.isBlank()) "جفت نشده" else "متصل" +
                        " | Laptop: " +
                        if (localToken.isBlank()) "جفت نشده" else "متصل"
                }
            ) {
                Text("وضعیت")
            }
        }

        Text(
            "وضعیت: " + status,
            style = MaterialTheme.typography.bodySmall
        )

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
