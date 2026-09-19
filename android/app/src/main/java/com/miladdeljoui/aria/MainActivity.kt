package com.miladdeljoui.aria

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import java.util.Locale
import java.util.concurrent.Executors
import kotlin.math.cos
import kotlin.math.sin

private data class ChatItem(val owner: Boolean, val text: String)

private val AriaCyan = Color(0xFF00E5FF)
private val AriaCyanSoft = Color(0x2200E5FF)
private val AriaBackground = Color(0xFF0B1220)
private val AriaPanel = Color(0xFF121A2B)
private val AriaPanelSoft = Color(0xFF1A2438)
private val AriaText = Color(0xFFE8F1FF)
private val AriaMuted = Color(0xFF8FA3C1)

class MainActivity : ComponentActivity() {
    private val askPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (!granted) {
            voiceStatus.value = "مجوز میکروفون داده نشد"
        }
    }

    private val voiceStatus = mutableStateOf("آماده")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AriaTheme {
                AriaApp(
                    voiceStatus = voiceStatus.value,
                    requestMicPermission = {
                        if (ContextCompat.checkSelfPermission(
                                this,
                                Manifest.permission.RECORD_AUDIO
                            ) == PackageManager.PERMISSION_GRANTED
                        ) {
                            Unit
                        } else {
                            askPermission.launch(Manifest.permission.RECORD_AUDIO)
                        }
                    }
                )
            }
        }
    }
}

@Composable
private fun AriaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = androidx.compose.material3.darkColorScheme(
            primary = AriaCyan,
            secondary = AriaCyan,
            background = AriaBackground,
            surface = AriaPanel,
            onBackground = AriaText,
            onSurface = AriaText
        ),
        content = content
    )
}

@Composable
private fun AriaApp(
    voiceStatus: String,
    requestMicPermission: () -> Unit
) {
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
    var status by remember { mutableStateOf("ARIA آماده است — کد ۶ رقمی ترمینال سرور را وارد کن") }
    var onlineMode by remember { mutableStateOf("CLOUD / LOCAL") }
    val messages = remember { mutableStateListOf<ChatItem>() }

    val tts = remember {
        TextToSpeech(context) { }
    }

    fun updateUi(block: () -> Unit) {
        uiHandler.post(block)
    }

    val voiceController = remember {
        VoiceController(
            context = context,
            onText = { recognized ->
                updateUi {
                    message = recognized
                    status = "متن صوتی آماده ارسال است"
                }
            },
            onState = { newState ->
                updateUi { status = newState }
            }
        )
    }

    DisposableEffect(Unit) {
        onDispose {
            voiceController.destroy()
            tts.shutdown()
            executor.shutdownNow()
        }
    }

    fun speak(text: String) {
        tts.language = Locale("fa", "IR")
        tts.setPitch(0.84f)
        tts.setSpeechRate(0.92f)
        tts.speak(
            text,
            TextToSpeech.QUEUE_FLUSH,
            null,
            "aria-answer"
        )
    }

    fun friendlyError(error: Exception): String {
        return when (error) {
            is AriaApi.AriaException -> error.message ?: "خطای ناشناخته"
            else -> error.message ?: "خطای ناشناخته"
        }
    }

    fun pairCloud() {
        if (cloudUrl.isBlank()) {
            status = "آدرس Cloud را وارد کن."
            return
        }
        if (pairingCode.filter { it.isDigit() }.length != 6) {
            status = "کد جفت‌سازی باید دقیقاً ۶ رقم باشد."
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
                    onlineMode = "CLOUD"
                    status = "Cloud متصل شد ✓"
                }
            } catch (error: Exception) {
                updateUi {
                    status = "خطای Cloud: " + friendlyError(error)
                }
            }
        }
    }

    fun pairLocal() {
        if (localUrl.isBlank()) {
            status = "آدرس لپ‌تاپ را وارد کن (مثلاً http://192.168.x.x:8765)"
            return
        }
        if (pairingCode.filter { it.isDigit() }.length != 6) {
            status = "کد جفت‌سازی باید دقیقاً ۶ رقم باشد. کد ترمینال سرور را ببین."
            return
        }

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
                    onlineMode = "LAPTOP"
                    status = "لپ‌تاپ متصل شد ✓"
                }
            } catch (error: Exception) {
                updateUi {
                    status = "خطای لپ‌تاپ: " + friendlyError(error)
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
                        // Fall through to laptop.
                    }
                }

                if (response == null && localToken.isNotBlank() && localUrl.isNotBlank()) {
                    response = api.chat(localUrl, localToken, prompt)
                    source = "Laptop"
                }

                if (response == null) {
                    error("هیچ اتصال به ARIA موجود نیست. ابتدا جفت‌سازی کن.")
                }

                val result = response ?: error("پاسخ دریافت نشد.")
                val approvalText = if (result.requiresApproval) {
                    "\n\n🔐 نیازمند تأیید مالک: " + result.permissionLevel
                } else {
                    ""
                }

                updateUi {
                    onlineMode = source.uppercase(Locale.ROOT)
                    status = "پاسخ از $source"
                    messages.add(
                        ChatItem(
                            owner = false,
                            text = result.answer + approvalText
                        )
                    )
                    speak(result.answer)
                }
            } catch (error: Exception) {
                updateUi {
                    status = "ارتباط برقرار نشد"
                    messages.add(
                        ChatItem(
                            owner = false,
                            text = "ARIA: " + friendlyError(error)
                        )
                    )
                }
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(AriaBackground)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    "ARIA",
                    style = MaterialTheme.typography.headlineLarge,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    "PERSONAL INTELLIGENCE CORE",
                    color = AriaMuted,
                    style = MaterialTheme.typography.labelSmall
                )
            }

            Text(
                onlineMode,
                color = AriaCyan,
                style = MaterialTheme.typography.labelSmall
            )
        }

        Box(
            modifier = Modifier.fillMaxWidth(),
            contentAlignment = Alignment.Center
        ) {
            AriaEye()
        }

        Text(
            status,
            color = AriaMuted,
            style = MaterialTheme.typography.bodySmall
        )

        Text(
            voiceStatus,
            color = AriaMuted,
            style = MaterialTheme.typography.bodySmall
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = cloudUrl,
                onValueChange = { cloudUrl = it },
                modifier = Modifier.weight(1f),
                label = { Text("Cloud") },
                placeholder = { Text("https://...") }
            )
            OutlinedButton(onClick = { pairCloud() }) {
                Text("اتصال")
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = localUrl,
                onValueChange = { localUrl = it },
                modifier = Modifier.weight(1f),
                label = { Text("Laptop") }
            )
            OutlinedButton(onClick = { pairLocal() }) {
                Text("اتصال")
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = pairingCode,
                onValueChange = { pairingCode = it.filter { ch -> ch.isDigit() }.take(6) },
                modifier = Modifier.weight(1f),
                label = { Text("کد ۶ رقمی مالک") },
                placeholder = { Text("مثلاً 482917") }
            )
            Button(
                onClick = requestMicPermission,
                colors = ButtonDefaults.buttonColors(
                    containerColor = AriaCyanSoft,
                    contentColor = AriaCyan
                )
            ) {
                Text("مجوز صدا")
            }
        }

        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .clip(RoundedCornerShape(18.dp))
                .background(AriaPanel)
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(messages) { item ->
                Text(
                    text = (if (item.owner) "تو  ›  " else "ARIA  ›  ") + item.text,
                    color = if (item.owner) AriaText else AriaCyan,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                onClick = {
                    if (ContextCompat.checkSelfPermission(
                            context,
                            Manifest.permission.RECORD_AUDIO
                        ) == PackageManager.PERMISSION_GRANTED
                    ) {
                        voiceController.start()
                    } else {
                        requestMicPermission()
                    }
                },
                modifier = Modifier.size(58.dp),
                shape = CircleShape
            ) {
                Text("🎙")
            }

            OutlinedTextField(
                value = message,
                onValueChange = { message = it },
                modifier = Modifier.weight(1f),
                label = { Text("با ARIA صحبت کن") }
            )

            Button(
                onClick = { sendMessage() },
                modifier = Modifier.height(58.dp)
            ) {
                Text("ارسال")
            }
        }

        Text(
            "صوت فارسی: تشخیص گفتار دستگاه + TTS محلی",
            color = AriaMuted,
            style = MaterialTheme.typography.labelSmall
        )
    }
}

@Composable
private fun AriaEye() {
    val transition = rememberInfiniteTransition(label = "aria-eye")
    val pulse by transition.animateFloat(
        initialValue = 0.92f,
        targetValue = 1.06f,
        animationSpec = infiniteRepeatable(
            animation = tween(
                durationMillis = 1600,
                easing = FastOutSlowInEasing
            ),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )
    val sweep by transition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(
                durationMillis = 3600
            )
        ),
        label = "sweep"
    )

    Canvas(modifier = Modifier.size(220.dp)) {
        drawEye(pulse, sweep)
    }
}

private fun DrawScope.drawEye(scale: Float, rotation: Float) {
    val center = Offset(size.width / 2f, size.height / 2f)
    val radius = 82f * scale

    drawCircle(
        color = AriaCyan.copy(alpha = 0.08f),
        radius = radius + 22f
    )
    drawCircle(
        color = AriaCyan.copy(alpha = 0.14f),
        radius = radius + 10f,
        style = Stroke(width = 2f)
    )

    val eye = Path().apply {
        moveTo(center.x - 72f, center.y)
        quadraticBezierTo(
            center.x,
            center.y - 58f,
            center.x + 72f,
            center.y
        )
        quadraticBezierTo(
            center.x,
            center.y + 58f,
            center.x - 72f,
            center.y
        )
        close()
    }

    drawPath(
        eye,
        color = AriaPanelSoft,
        style = Stroke(width = 5f)
    )

    drawCircle(
        color = AriaCyan.copy(alpha = 0.18f),
        radius = 38f * scale
    )
    drawCircle(
        color = AriaCyan,
        radius = 24f * scale
    )
    drawCircle(
        color = AriaBackground,
        radius = 11f * scale
    )
    drawCircle(
        color = AriaText.copy(alpha = 0.9f),
        radius = 4f
    )

    drawArc(
        color = AriaCyan,
        startAngle = rotation,
        sweepAngle = 70f,
        useCenter = false,
        topLeft = Rect(center.x - radius, center.y - radius, 2f * radius, 2f * radius),
        style = Stroke(width = 4f, cap = StrokeCap.Round)
    )

    drawArc(
        color = AriaCyan.copy(alpha = 0.35f),
        startAngle = rotation + 180f,
        sweepAngle = 55f,
        useCenter = false,
        topLeft = Rect(center.x - radius, center.y - radius, 2f * radius, 2f * radius),
        style = Stroke(width = 2f, cap = StrokeCap.Round)
    )

    for (index in 0 until 8) {
        val angle = (index * 45f + rotation) * Math.PI / 180.0
        val inner = radius + 18f
        val outer = radius + if (index % 2 == 0) 30f else 24f

        drawLine(
            color = AriaCyan.copy(alpha = if (index % 2 == 0) 0.7f else 0.28f),
            start = Offset(
                center.x + cos(angle).toFloat() * inner,
                center.y + sin(angle).toFloat() * inner
            ),
            end = Offset(
                center.x + cos(angle).toFloat() * outer,
                center.y + sin(angle).toFloat() * outer
            ),
            strokeWidth = 2f,
            cap = StrokeCap.Round
        )
    }

    drawCircle(
        color = AriaText.copy(alpha = 0.8f),
        radius = 2.5f,
        center = Offset(center.x + 34f, center.y - 24f)
    )
}
