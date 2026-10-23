package com.miladdeljoui.aria

import android.Manifest
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
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
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import java.util.Locale
import java.util.concurrent.Executors
import kotlin.math.cos
import kotlin.math.sin

private data class ChatItem(val owner: Boolean, val text: String)

// پالت نزدیک به حس شیشه‌ای / فیروزه‌ای فیلم (الهام بصری، نه کپی)
private val AriaCyanDim = Color(0xFF2DD4BF)
private val AriaGlass = Color(0x22A7F3D0)

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
                AriaRoot(
                    voiceStatus = voiceStatus,
                    requestMicPermission = {
                        if (ContextCompat.checkSelfPermission(
                                this,
                                Manifest.permission.RECORD_AUDIO
                            ) != PackageManager.PERMISSION_GRANTED
                        ) {
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
            secondary = AriaCyanDim,
            background = AriaBackground,
            surface = AriaPanel,
            onBackground = AriaText,
            onSurface = AriaText
        ),
        content = content
    )
}

@Composable
private fun AriaRoot(
    voiceStatus: androidx.compose.runtime.MutableState<String>,
    requestMicPermission: () -> Unit
) {
    val context = LocalContext.current
    val prefs = remember {
        context.getSharedPreferences("aria_profile", Context.MODE_PRIVATE)
    }
    var signedIn by remember { mutableStateOf(prefs.getBoolean("guest_ready", true)) }

    if (!signedIn) {
        GuestSignInScreen(
            initialName = prefs.getString("name", "") ?: "",
            initialPhone = prefs.getString("phone", "") ?: "",
            onContinue = { name, phone ->
                prefs.edit()
                    .putString("name", name.trim())
                    .putString("phone", phone.trim())
                    .putBoolean("guest_ready", true)
                    .apply()
                signedIn = true
            }
        )
    } else {
        AriaApp(
            voiceStatus = voiceStatus.value,
            requestMicPermission = requestMicPermission,
            onVoiceState = { voiceStatus.value = it }
        )
    }
}

@Composable
private fun GuestSignInScreen(
    initialName: String,
    initialPhone: String,
    onContinue: (String, String) -> Unit
) {
    var name by remember { mutableStateOf(initialName) }
    var phone by remember { mutableStateOf(initialPhone) }
    var error by remember { mutableStateOf("") }

    Box(
        modifier = Modifier.fillMaxSize().background(
            Brush.verticalGradient(listOf(Color(0xFF10172A), Color(0xFF07101B)))
        ),
        contentAlignment = Alignment.Center
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Text("ARIA", style = MaterialTheme.typography.headlineLarge, color = Color.White)
            Text("دستیار هوشمند شخصی تو", color = Color(0xFFB8C5D9))
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedButton(
                onClick = { error = "ورود گوگل هنوز به سرویس OAuth متصل نشده است." },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("G  ورود با حساب گوگل")
            }
            Text("یا ورود مهمان رایگان", color = Color(0xFF7DE3D1))
            OutlinedTextField(
                value = name,
                onValueChange = { name = it; error = "" },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("نام") },
                singleLine = true
            )
            OutlinedTextField(
                value = phone,
                onValueChange = { phone = it; error = "" },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("شماره تلفن") },
                singleLine = true
            )
            if (error.isNotBlank()) {
                Text(error, color = Color(0xFFFFB4AB))
            }
            Button(
                onClick = {
                    if (name.trim().isBlank()) {
                        error = "نامت را وارد کن."
                    } else if (phone.trim().filter { it.isDigit() }.length < 7) {
                        error = "شماره تلفن را بررسی کن."
                    } else {
                        onContinue(name, phone)
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("ادامه به‌صورت مهمان")
            }
            Text(
                "نام و شماره فعلاً فقط روی همین گوشی ذخیره می‌شوند؛ پیامک تأیید ارسال نمی‌شود.",
                color = Color(0xFF9BAAC0),
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

@Composable
private fun AriaApp(
    voiceStatus: String,
    requestMicPermission: () -> Unit,
    onVoiceState: (String) -> Unit
) {
    val context = LocalContext.current
    val prefs = remember {
        context.getSharedPreferences("aria", Context.MODE_PRIVATE)
    }
    val uiHandler = remember { Handler(Looper.getMainLooper()) }
    val executor = remember { Executors.newSingleThreadExecutor() }
    val api = remember { AriaApi() }

    var cloudUrl by remember {
        mutableStateOf(prefs.getString("cloud_url", "https://aria-2.weblines.ir") ?: "https://aria-2.weblines.ir")
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
    var showPackages by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("هسته باز است — به آرامی مشاهده می‌کند") }
    var onlineMode by remember { mutableStateOf("STANDBY") }
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
                updateUi { onVoiceState(newState) }
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
        tts.setPitch(0.88f)
        tts.setSpeechRate(0.90f)
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "aria-answer")
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
                val token = api.pair(cloudUrl, pairingCode, "ARIA Android Cloud")
                prefs.edit()
                    .putString("cloud_url", cloudUrl.trimEnd('/'))
                    .putString("cloud_token", token)
                    .apply()
                updateUi {
                    cloudToken = token
                    onlineMode = "CLOUD"
                    status = "Cloud متصل شد"
                }
            } catch (error: Exception) {
                updateUi { status = "Cloud: " + friendlyError(error) }
            }
        }
    }

    fun pairLocal() {
        if (localUrl.isBlank()) {
            status = "آدرس لپ‌تاپ را وارد کن"
            return
        }
        if (pairingCode.filter { it.isDigit() }.length != 6) {
            status = "کد ۶ رقمی ترمینال سرور لازم است"
            return
        }
        executor.execute {
            try {
                val token = api.pair(localUrl, pairingCode, "ARIA Android Local")
                prefs.edit()
                    .putString("local_url", localUrl.trimEnd('/'))
                    .putString("local_token", token)
                    .apply()
                updateUi {
                    localToken = token
                    onlineMode = "LOCAL"
                    status = "لپ‌تاپ متصل شد"
                }
            } catch (error: Exception) {
                updateUi { status = "لپ‌تاپ: " + friendlyError(error) }
            }
        }
    }

    fun sendMessage() {
        val prompt = message.trim()
        if (prompt.isBlank()) return
        messages.add(ChatItem(true, prompt))
        message = ""

        executor.execute {
            try {
                var response: AriaResponse? = null
                var source = ""

                // Local-first: keeps chat usable on the home LAN if public internet is blocked.
                if (localToken.isNotBlank() && localUrl.isNotBlank()) {
                    try {
                        response = api.chat(localUrl, localToken, prompt)
                        source = "Local"
                    } catch (_: Exception) {
                    }
                }
                if (response == null && cloudToken.isNotBlank() && cloudUrl.isNotBlank()) {
                    response = api.chat(cloudUrl, cloudToken, prompt)
                    source = "Cloud"
                }
                if (response == null) {
                    error("اتصال به ARIA نیست. اول جفت‌سازی کن. اگر ollama_unavailable دیدی روی لپ‌تاپ: ollama serve")
                }

                val result = response!!
                val approval = if (result.requiresApproval) {
                    "\n\nنیازمند تأیید مالک · ${result.permissionLevel}"
                } else ""

                updateUi {
                    onlineMode = source.uppercase(Locale.ROOT)
                    status = "پاسخ از $source"
                    messages.add(ChatItem(false, result.answer + approval))
                    speak(result.answer)
                }
            } catch (error: Exception) {
                updateUi {
                    status = "قطع ارتباط"
                    messages.add(ChatItem(false, friendlyError(error)))
                }
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(AriaBackground)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text("ARIA", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Light, color = AriaCyan)
                Text("OBSERVING · LOCAL CORE", color = AriaMuted, style = MaterialTheme.typography.labelSmall)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(onlineMode, color = AriaCyan, style = MaterialTheme.typography.labelSmall)
                OutlinedButton(onClick = { showPackages = true }) { Text("بسته‌ها") }
            }
        }

        Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center, content = {
            AvaCore(listening = voiceStatus.contains("شن") || voiceStatus.contains("پردازش"))
        })

        Text(status, color = AriaMuted, style = MaterialTheme.typography.bodySmall)
        Text(voiceStatus, color = AriaMuted, style = MaterialTheme.typography.labelSmall)

        Text("اتصال جایگزین اینترنت", color = AriaCyan, style = MaterialTheme.typography.labelMedium)
        Text(
            "یکی از VPNهای جداگانه را نصب و وصل کن؛ ARIA خودش تونل VPN را مدیریت نمی‌کند.",
            color = AriaMuted,
            style = MaterialTheme.typography.bodySmall
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(
                onClick = {
                    context.startActivity(
                        Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/shirokhorshid/shirokhorshid-android/releases"))
                    )
                },
                modifier = Modifier.weight(1f)
            ) { Text("شیر و خورشید") }
            OutlinedButton(
                onClick = {
                    context.startActivity(
                        Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/GFW-knocker/MahsaNG/releases/latest"))
                    )
                },
                modifier = Modifier.weight(1f)
            ) { Text("مهسا") }
        }
        OutlinedButton(
            onClick = {
                context.startActivity(
                    Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=org.torproject.android"))
                )
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Orbot / Tor") }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = cloudUrl,
                onValueChange = { cloudUrl = it },
                modifier = Modifier.weight(1f),
                label = { Text("Cloud") }
            )
            OutlinedButton(onClick = { pairCloud() }) { Text("اتصال") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = localUrl,
                onValueChange = { localUrl = it },
                modifier = Modifier.weight(1f),
                label = { Text("Laptop") }
            )
            OutlinedButton(onClick = { pairLocal() }) { Text("اتصال") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = pairingCode,
                onValueChange = { pairingCode = it.filter { c -> c.isDigit() }.take(6) },
                modifier = Modifier.weight(1f),
                label = { Text("کد ۶ رقمی") }
            )
            Button(
                onClick = requestMicPermission,
                colors = ButtonDefaults.buttonColors(containerColor = AriaCyanSoft, contentColor = AriaCyan)
            ) { Text("مجوز صدا") }
        }

        LazyColumn(
            modifier = Modifier
                .height(220.dp)
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(AriaPanel)
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(messages) { item ->
                Text(
                    text = (if (item.owner) "تو · " else "ARIA · ") + item.text,
                    color = if (item.owner) AriaText else AriaCyan,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                onClick = {
                    if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
                        == PackageManager.PERMISSION_GRANTED
                    ) {
                        voiceController.start()
                    } else requestMicPermission()
                },
                modifier = Modifier.size(56.dp),
                shape = CircleShape
            ) { Text("🎙") }

            OutlinedTextField(
                value = message,
                onValueChange = { message = it },
                modifier = Modifier.weight(1f),
                label = { Text("با ARIA حرف بزن") }
            )
            Button(onClick = { sendMessage() }, modifier = Modifier.height(56.dp)) {
                Text("ارسال")
            }
        }

        if (showPackages) {
            val persianDate = remember {
                java.text.SimpleDateFormat("yyyy/MM/dd", Locale("fa", "IR")).format(java.util.Date())
                    .map { ch -> if (ch in '0'..'9') "۰۱۲۳۴۵۶۷۸۹"[ch - '0'] else ch }
                    .joinToString("")
            }
            androidx.compose.material3.AlertDialog(
                onDismissRequest = { showPackages = false },
                title = { Text("بسته‌های اشتراک ARIA") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text("تاریخ امروز: $persianDate", color = AriaCyan)
                        Text("دوره آزمایشی", fontWeight = FontWeight.Bold)
                        Text("۳۰ روز رایگان برای کاربران جدید در دوره بتا")
                        Text("بسته ماهانه", fontWeight = FontWeight.Bold)
                        Text("۹۹٬۰۰۰ تومان برای هر ماه")
                        Text("پس از پایان دوره آزمایشی")
                        Text(
                            "توجه: پرداخت آنلاین هنوز فعال نشده است؛ فعلاً از داخل این صفحه پولی پرداخت نکن.",
                            color = AriaMuted,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                },
                confirmButton = {
                    Button(onClick = { showPackages = false }) { Text("متوجه شدم") }
                },
                containerColor = AriaPanel,
                titleContentColor = AriaCyan,
                textContentColor = AriaText
            )
        }
    }
}

@Composable
private fun AvaCore(listening: Boolean) {
    val transition = rememberInfiniteTransition(label = "ava")
    val pulse by transition.animateFloat(
        initialValue = 0.96f,
        targetValue = 1.04f,
        animationSpec = infiniteRepeatable(
            animation = tween(2200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )
    val sweep by transition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(8000, easing = LinearEasing)
        ),
        label = "sweep"
    )
    val blink by transition.animateFloat(
        initialValue = 1f,
        targetValue = if (listening) 1f else 0.15f,
        animationSpec = infiniteRepeatable(
            animation = tween(if (listening) 400 else 3200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "blink"
    )

    Canvas(modifier = Modifier.size(200.dp)) {
        drawAvaCore(pulse, sweep, blink, listening)
    }
}

private fun DrawScope.drawAvaCore(scale: Float, rotation: Float, lid: Float, listening: Boolean) {
    val center = Offset(size.width / 2f, size.height / 2f)
    val radius = 70f * scale

    // هاله شیشه‌ای
    drawCircle(color = AriaGlass, radius = radius + 28f)
    drawCircle(
        color = AriaCyan.copy(alpha = 0.12f),
        radius = radius + 14f,
        style = Stroke(width = 1.5f)
    )

    // قاب چشم بیضی نرم
    val eye = Path().apply {
        moveTo(center.x - 64f, center.y)
        quadraticBezierTo(center.x, center.y - 48f * lid, center.x + 64f, center.y)
        quadraticBezierTo(center.x, center.y + 48f * lid, center.x - 64f, center.y)
        close()
    }
    drawPath(eye, color = AriaPanelSoft, style = Stroke(width = 3f))

    // مردمک
    drawCircle(color = AriaCyan.copy(alpha = 0.2f), radius = 32f * scale * lid)
    drawCircle(color = AriaCyanDim.copy(alpha = 0.85f), radius = 18f * scale * lid)
    drawCircle(color = AriaBackground, radius = 8f * scale * lid)
    drawCircle(color = AriaText.copy(alpha = 0.9f), radius = 3f * lid)

    // حلقه اسکن آرام
    drawArc(
        color = AriaCyan.copy(alpha = if (listening) 0.9f else 0.45f),
        startAngle = rotation,
        sweepAngle = if (listening) 100f else 55f,
        useCenter = false,
        topLeft = Offset(center.x - radius, center.y - radius),
        size = Size(2f * radius, 2f * radius),
        style = Stroke(width = 2.5f, cap = StrokeCap.Round)
    )

    // خطوط شبکه ظریف (حس مش چهره — انتزاعی)
    for (i in 0 until 6) {
        val a = (i * 60f + rotation * 0.3f) * Math.PI / 180.0
        drawLine(
            color = AriaCyan.copy(alpha = 0.2f),
            start = Offset(center.x + cos(a).toFloat() * (radius - 8f), center.y + sin(a).toFloat() * (radius - 8f)),
            end = Offset(center.x + cos(a).toFloat() * (radius + 10f), center.y + sin(a).toFloat() * (radius + 10f)),
            strokeWidth = 1.2f,
            cap = StrokeCap.Round
        )
    }
}
