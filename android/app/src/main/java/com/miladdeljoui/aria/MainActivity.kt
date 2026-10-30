package com.miladdeljoui.aria

import android.Manifest
import android.graphics.BitmapFactory
import android.util.Base64
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
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import java.util.Locale
import java.util.UUID
import java.util.concurrent.Executors
import kotlin.math.cos
import kotlin.math.sin

private data class ChatItem(val owner: Boolean, val text: String, val imageBase64: String? = null, val videoUrl: String? = null)

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
    val mediaExecutor = remember { Executors.newSingleThreadExecutor() }
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
    var composerMode by remember { mutableStateOf("chat") }
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

    LaunchedEffect(cloudUrl) {
        status = "در حال بررسی اتصال ARIA…"
        executor.execute {
            try {
                val server = api.status(cloudUrl.trimEnd('/'))
                val configured = server.optBoolean("cloud_ai_configured", false)
                val provider = server.optString("ai_provider", "cloud").uppercase(Locale.ROOT)
                updateUi {
                    onlineMode = if (configured) provider else "SERVER"
                    status = if (configured) {
                        "سرور پاسخ می‌دهد؛ موتور $provider تنظیم شده است."
                    } else {
                        "سرور در دسترس است، اما کلید موتور هوش مصنوعی هنوز تنظیم نشده؛ مسیر رایگان جایگزین هنگام ارسال امتحان می‌شود."
                    }
                }
            } catch (error: Exception) {
                updateUi {
                    onlineMode = "STANDBY"
                    status = "سرور ARIA پاسخ نداد؛ هنگام ارسال مسیر رایگان جایگزین را هم امتحان می‌کنیم."
                }
            }
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            voiceController.destroy()
            tts.shutdown()
            executor.shutdownNow()
            mediaExecutor.shutdownNow()
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

    fun guestToken(forceRegister: Boolean = false): String {
        val saved = prefs.getString("cloud_token", "") ?: ""
        if (!forceRegister && saved.isNotBlank()) return saved
        val installId = prefs.getString("guest_install_id", null)
            ?: UUID.randomUUID().toString().also {
                prefs.edit().putString("guest_install_id", it).apply()
            }
        if (cloudUrl.isBlank()) throw IllegalStateException("آدرس سرور خالی است.")
        val token = api.guest(cloudUrl.trimEnd('/'), installId, "ARIA Android")
        prefs.edit()
            .putString("cloud_url", cloudUrl.trimEnd('/'))
            .putString("cloud_token", token)
            .apply()
        updateUi {
            cloudToken = token
            onlineMode = "CLOUD"
            status = "اتصال مهمان برقرار شد."
        }
        return token
    }

    fun reconnectCloud() {
        status = "در حال اتصال خودکار به سرور ARIA…"
        executor.execute {
            try {
                val token = guestToken(forceRegister = true)
                val server = api.status(cloudUrl.trimEnd('/'))
                val aiReady = server.optBoolean("cloud_ai_configured", false) || server.optBoolean("ollama", false)
                updateUi {
                    cloudToken = token
                    onlineMode = "CLOUD"
                    status = if (aiReady) "سرور و موتور هوش مصنوعی آماده‌اند." else "سرور در دسترس است، اما مدل هوش مصنوعی هنوز تنظیم نشده."
                }
            } catch (error: Exception) {
                updateUi { onlineMode = "STANDBY"; status = "اتصال ناموفق: " + friendlyError(error) }
            }
        }
    }

    fun sendMessage() {
        val prompt = message.trim()
        if (prompt.isBlank()) return
        val mode = composerMode
        val history = messages.takeLast(12).map { item -> Pair(if (item.owner) "user" else "assistant", item.text) }
        messages.add(ChatItem(true, prompt))
        message = ""
        composerMode = "chat"

        if (mode == "image") {
            updateUi { status = "در حال ساخت تصویر از طریق سرور امن ARIA؛ ممکن است هزینهٔ سرویس‌دهنده اعمال شود." }
            mediaExecutor.execute {
                try {
                    val token = guestToken()
                    val media = api.generateImage(cloudUrl.trimEnd('/'), token, prompt)
                    val base64 = media.optString("image_base64")
                    if (base64.isBlank()) throw IllegalStateException("سرور تصویر خالی برگرداند.")
                    updateUi {
                        messages.add(ChatItem(false, "تصویر آماده شد · ${media.optString("model", "ARIA")}", imageBase64 = base64))
                        status = "تصویر آماده شد."
                    }
                } catch (error: Exception) {
                    updateUi { messages.add(ChatItem(false, friendlyError(error))); status = "ساخت تصویر انجام نشد." }
                }
            }
            return
        }

        if (mode == "video") {
            updateUi { status = "در حال ساخت کلیپ از طریق سرور؛ ممکن است چند دقیقه و اعتبار سرویس لازم باشد." }
            mediaExecutor.execute {
                try {
                    val token = guestToken()
                    val media = api.generateVideo(cloudUrl.trimEnd('/'), token, prompt, duration = 5)
                    val base64 = media.optString("video_base64")
                    if (base64.isBlank()) throw IllegalStateException("سرور کلیپ آماده برنگرداند.")
                    val videoUri = api.saveVideoBase64(context, base64)
                    updateUi {
                        messages.add(ChatItem(false, "کلیپ آماده شد · ${media.optString("model", "ARIA")}", videoUrl = videoUri))
                        status = "کلیپ آماده شد."
                    }
                } catch (error: Exception) {
                    updateUi { messages.add(ChatItem(false, friendlyError(error))); status = "ساخت کلیپ انجام نشد." }
                }
            }
            return
        }

        executor.execute {
            try {
                var response: AriaResponse? = null
                var source = ""
                var serverError: Exception? = null

                try {
                    var token = guestToken()
                    try {
                        response = api.chat(cloudUrl.trimEnd('/'), token, prompt, history)
                    } catch (firstError: Exception) {
                        if (firstError is AriaApi.AriaException && firstError.errorCode == "unauthorized") {
                            token = guestToken(forceRegister = true)
                            response = api.chat(cloudUrl.trimEnd('/'), token, prompt, history)
                        } else {
                            throw firstError
                        }
                    }
                    source = "سرور ARIA"
                } catch (error: Exception) {
                    serverError = error
                }

                if (response == null) {
                    try {
                        response = api.freeChat(prompt, history)
                        source = "OVH جایگزین"
                    } catch (directError: Exception) {
                        val serverMessage = serverError?.message?.takeIf { it.isNotBlank() }
                            ?: "سرور ARIA در دسترس نیست."
                        throw IllegalStateException("$serverMessage\nمسیر جایگزین هم پاسخ نداد: ${directError.message ?: "خطای ارتباط"}")
                    }
                }
                if (response == null) throw IllegalStateException("مدل هوش مصنوعی پاسخ نداد.")
                val result = response!!
                val approval = if (result.requiresApproval) "\n\nنیازمند تأیید مالک · ${result.permissionLevel}" else ""
                updateUi {
                    onlineMode = source.uppercase(Locale.ROOT)
                    status = "پاسخ از $source"
                    messages.add(ChatItem(false, result.answer + approval))
                    speak(result.answer)
                }
            } catch (error: Exception) {
                updateUi {
                    status = "پاسخی دریافت نشد"
                    messages.add(ChatItem(false, friendlyError(error)))
                }
            }
        }
    }

    var showSettings by remember { mutableStateOf(false) }
    var showFeedback by remember { mutableStateOf(false) }
    var feedbackText by remember { mutableStateOf("") }
    var feedbackCategory by remember { mutableStateOf("idea") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(Color(0xFF171715), Color(0xFF1C1B19), Color(0xFF171715))
                )
            )
    ) {
        Column(
            modifier = Modifier.fillMaxSize().imePadding().padding(horizontal = 18.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(
                        modifier = Modifier.size(42.dp).clip(CircleShape)
                            .background(Brush.radialGradient(listOf(Color(0xFFE9A17A), Color(0xFFC66A49), Color(0xFF34201A)))),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("A", color = Color.White, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleLarge)
                    }
                    Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                        Text("ARIA", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.SemiBold, color = Color(0xFFF4F7FF))
                        Text("دستیار هوشمند فارسی", color = Color(0xFF9AB6D8), style = MaterialTheme.typography.labelSmall)
                    }
                }
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(
                        modifier = Modifier.clip(RoundedCornerShape(50)).background(Color(0xFF2B2926)).padding(horizontal = 10.dp, vertical = 7.dp)
                    ) {
                        Text(onlineMode, color = Color(0xFFE5A080), style = MaterialTheme.typography.labelSmall)
                    }
                    OutlinedButton(onClick = { messages.clear(); composerMode = "chat"; message = "" }, contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 10.dp, vertical = 8.dp)) { Text("＋") }
                    OutlinedButton(onClick = { showSettings = true }, contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 10.dp, vertical = 8.dp)) { Text("تنظیمات") }
                }
            }

            if (messages.isEmpty()) {
                Column(
                    modifier = Modifier.fillMaxWidth().weight(1f),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Box(
                        modifier = Modifier.size(56.dp).clip(CircleShape).background(Color(0xFF36271F)),
                        contentAlignment = Alignment.Center
                    ) { Text("✳", color = Color(0xFFE5A080), style = MaterialTheme.typography.headlineMedium) }
                    Spacer(Modifier.height(20.dp))
                    Text("سلام! من آریا هستم.", color = Color(0xFFF4F7FF), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(8.dp))
                    Text("امروز چه چیزی را با هم حل کنیم؟", color = Color(0xFFAAB7D0))
                    Spacer(Modifier.height(18.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { message = "یک برنامهٔ یادگیری هوش مصنوعی برای من طراحی کن." }) { Text("یادگیری AI") }
                        OutlinedButton(onClick = { message = "این ایده را به یک پروژهٔ عملی تبدیل کن." }) { Text("ایده‌پردازی") }
                    }
                }
            } else {
                Column(
                    modifier = Modifier.fillMaxWidth().height(54.dp),
                    verticalArrangement = Arrangement.Center
                ) {
                    Text("گفت‌وگو", color = AriaText, fontWeight = FontWeight.SemiBold)
                    Text("گفت‌وگوی فارسی با ARIA", color = Color(0xFF8F9BB5), style = MaterialTheme.typography.labelSmall)
                }
            }

            Column(
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp))
                    .background(Color(0xFF22211F)).padding(horizontal = 14.dp, vertical = 10.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(
                    when (onlineMode) {
                        "STANDBY" -> "در انتظار اتصال"
                        else -> "اتصال برقرار است"
                    },
                    color = if (onlineMode == "STANDBY") Color(0xFFE5A080) else Color(0xFFB5C9B5),
                    fontWeight = FontWeight.Medium
                )
                Text(status, color = AriaMuted, style = MaterialTheme.typography.bodySmall)
                if (voiceStatus != "آماده") Text(voiceStatus, color = Color(0xFF9DABCA), style = MaterialTheme.typography.labelSmall)
            }

            if (messages.isNotEmpty()) {
                LazyColumn(
                    modifier = Modifier.weight(1f).fillMaxWidth()
                        .clip(RoundedCornerShape(20.dp))
                        .background(Color.Transparent)
                        .padding(horizontal = 4.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(messages) { item ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = if (item.owner) Arrangement.End else Arrangement.Start
                        ) {
                            Column(
                                modifier = Modifier.fillMaxWidth(if (item.owner) 0.88f else 0.96f)
                                    .clip(RoundedCornerShape(18.dp))
                                    .background(if (item.owner) Color(0xFF2B2926) else Color.Transparent)
                                    .padding(horizontal = 12.dp, vertical = 10.dp)
                            ) {
                                Text(if (item.owner) "شما" else "ARIA", color = if (item.owner) Color(0xFFE5A080) else Color(0xFFBAB2A8), style = MaterialTheme.typography.labelSmall)
                                Spacer(Modifier.height(5.dp))
                                Text(item.text, color = AriaText)
                                val imageBitmap = remember(item.imageBase64) {
                                    item.imageBase64?.let { encoded ->
                                        runCatching {
                                            val bytes = Base64.decode(encoded, Base64.DEFAULT)
                                            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
                                        }.getOrNull()
                                    }
                                }
                                if (imageBitmap != null) {
                                    Spacer(Modifier.height(10.dp))
                                    Image(
                                        bitmap = imageBitmap,
                                        contentDescription = "تصویر تولیدشده توسط ARIA",
                                        modifier = Modifier.fillMaxWidth().heightIn(max = 360.dp).clip(RoundedCornerShape(12.dp))
                                    )
                                }
                                if (!item.videoUrl.isNullOrBlank()) {
                                    Spacer(Modifier.height(10.dp))
                                    OutlinedButton(onClick = {
                                        runCatching {
                                            context.startActivity(
                                                Intent(Intent.ACTION_VIEW, Uri.parse(item.videoUrl))
                                                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                            )
                                        }.onFailure { status = "بازکردن کلیپ ناموفق بود." }
                                    }, modifier = Modifier.fillMaxWidth()) { Text("▶ نمایش کلیپ") }
                                }
                            }
                        }
                    }
                }
            } else {
                Spacer(Modifier.weight(0.08f))
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(onClick = { composerMode = "chat" }, modifier = Modifier.weight(1f)) {
                    Text(if (composerMode == "chat") "✓ چت" else "چت")
                }
                OutlinedButton(onClick = { composerMode = "image"; status = "ساخت تصویر: ممکن است اعتبار پولی لازم باشد." }, modifier = Modifier.weight(1f)) {
                    Text(if (composerMode == "image") "✓ تصویر" else "تصویر")
                }
                OutlinedButton(onClick = { composerMode = "video"; status = "ساخت کلیپ: معمولاً پولی است و ممکن است چند دقیقه زمان ببرد." }, modifier = Modifier.weight(1f)) {
                    Text(if (composerMode == "video") "✓ کلیپ" else "کلیپ")
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp))
                    .background(Color(0xFF242320)).padding(6.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                OutlinedButton(
                    onClick = {
                        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                            voiceController.start()
                        } else requestMicPermission()
                    },
                    modifier = Modifier.size(48.dp),
                    shape = CircleShape,
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)
                ) { Text("🎙") }

                OutlinedTextField(
                    value = message,
                    onValueChange = { message = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text(when (composerMode) { "image" -> "توصیف تصویر دلخواه…"; "video" -> "توصیف کلیپ دلخواه…"; else -> "پیامت را برای ARIA بنویس…" }) },
                    singleLine = false,
                    maxLines = 4,
                    shape = RoundedCornerShape(18.dp)
                )
                Button(
                    onClick = { sendMessage() },
                    modifier = Modifier.size(48.dp),
                    shape = CircleShape,
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                    enabled = message.isNotBlank(),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC87956), contentColor = Color.White)
                ) { Text("➤") }
            }
        }
    }

    if (showSettings) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showSettings = false },
            title = { Text("تنظیمات ARIA") },
            text = {
                Column(
                    modifier = Modifier.verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("چت مستقیم و رایگان", color = AriaCyan, fontWeight = FontWeight.SemiBold)
                    Text("آزمایشگاه GPU در Molab", color = AriaCyan, fontWeight = FontWeight.SemiBold)
                    Text(
                        "این محیط برای آزمایش شخصی مدل‌ها در Notebook است؛ GPU آن به چت یا ساخت رسانهٔ ARIA وصل نمی‌شود و نباید به API عمومی یا پراکسی تبدیل شود.",
                        color = AriaMuted,
                        style = MaterialTheme.typography.bodySmall
                    )
                    OutlinedButton(
                        onClick = {
                            runCatching {
                                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://molab.marimo.io/")))
                            }.onFailure {
                                status = "بازکردن Molab ناموفق بود."
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("بازکردن آزمایشگاه Molab") }
                    Text("چت از موتور رایگان مستقل از سرور ARIA استفاده می‌کند. کد شش‌رقمی جفت‌سازی لازم نیست.", color = AriaMuted)
                    OutlinedTextField(
                        value = cloudUrl,
                        onValueChange = { cloudUrl = it.trim() },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("آدرس سرور ARIA") },
                        singleLine = true
                    )
                    Button(
                        onClick = {
                            prefs.edit().putString("cloud_url", cloudUrl.trimEnd('/')).apply()
                            reconnectCloud()
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("اتصال مجدد به سرور") }
                    Text(
                        "چت، ساخت تصویر و ساخت کلیپ از سرور ARIA انجام می‌شود. کلیدهای محرمانه فقط در تنظیمات خصوصی سرور نگهداری می‌شوند و داخل اپ قرار نمی‌گیرند.",
                        color = AriaMuted,
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        "ساخت تصویر و کلیپ هزینه یا سهمیهٔ جداگانه دارد و فقط بعد از فعال‌سازی مدیر سرور در دسترس است.",
                        color = AriaMuted,
                        style = MaterialTheme.typography.bodySmall
                    )
                    OutlinedButton(onClick = requestMicPermission, modifier = Modifier.fillMaxWidth()) { Text("فعال‌کردن میکروفون") }
                    OutlinedButton(
                        onClick = { showSettings = false; showFeedback = true },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("ارسال نظر و پیشنهاد") }
                    Text(status, color = AriaMuted, style = MaterialTheme.typography.bodySmall)
                    Text("چت رایگان به سهمیهٔ مدل وابسته است. ساخت تصویر و کلیپ ممکن است هزینه داشته باشد و فقط پس از فعال‌سازی در سرور کار می‌کند.", color = AriaMuted, style = MaterialTheme.typography.bodySmall)
                }
            },
            confirmButton = { Button(onClick = { showSettings = false }) { Text("بستن") } },
            containerColor = AriaPanel,
            titleContentColor = AriaCyan,
            textContentColor = AriaText
        )
    }

    if (showFeedback) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showFeedback = false },
            title = { Text("نظر و پیشنهاد برای ARIA") },
            text = {
                Column(
                    modifier = Modifier.verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("ایده یا ایرادت را مستقیم از داخل اپ برای سازنده بفرست.", color = AriaMuted)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        OutlinedButton(onClick = { feedbackCategory = "idea" }, modifier = Modifier.weight(1f)) {
                            Text(if (feedbackCategory == "idea") "✓ ایده" else "ایده")
                        }
                        OutlinedButton(onClick = { feedbackCategory = "bug" }, modifier = Modifier.weight(1f)) {
                            Text(if (feedbackCategory == "bug") "✓ ایراد" else "ایراد")
                        }
                        OutlinedButton(onClick = { feedbackCategory = "general" }, modifier = Modifier.weight(1f)) {
                            Text(if (feedbackCategory == "general") "✓ عمومی" else "عمومی")
                        }
                    }
                    OutlinedTextField(
                        value = feedbackText,
                        onValueChange = { feedbackText = it.take(4000) },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("پیام شما") },
                        placeholder = { Text("چه چیزی را بهتر کنیم؟") },
                        minLines = 4,
                        maxLines = 7
                    )
                    Text("برای ثبت نظر، اتصال اینترنت و دسترسی به سرور ARIA لازم است.", color = AriaMuted, style = MaterialTheme.typography.bodySmall)
                }
            },
            confirmButton = {
                Button(onClick = {
                    val messageToSend = feedbackText.trim()
                    val categoryToSend = feedbackCategory
                    val tokenToUse = if (localToken.isNotBlank()) localToken else cloudToken
                    val urlToUse = if (localToken.isNotBlank()) localUrl else cloudUrl
                    when {
                        messageToSend.length < 3 -> status = "پیام باید حداقل ۳ نویسه داشته باشد."
                        tokenToUse.isBlank() -> status = "ابتدا اتصال خودکار به سرور را از تنظیمات امتحان کن."
                        else -> executor.execute {
                            try {
                                api.sendFeedback(urlToUse, tokenToUse, categoryToSend, messageToSend, "0.7.0-beta1")
                                updateUi {
                                    status = "نظر تو ثبت شد؛ ممنون از همراهی‌ات!"
                                    feedbackText = ""
                                    showFeedback = false
                                }
                            } catch (error: Exception) {
                                updateUi { status = "ارسال نظر ناموفق بود: " + friendlyError(error) }
                            }
                        }
                    }
                }) { Text("ارسال نظر") }
            },
            dismissButton = {
                OutlinedButton(onClick = { showFeedback = false }) { Text("انصراف") }
            },
            containerColor = AriaPanel,
            titleContentColor = AriaCyan,
            textContentColor = AriaText
        )
    }

    if (showPackages) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showPackages = false },
            title = { Text("بسته‌های ARIA") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("نسخهٔ آزمایشی ARIA", color = AriaCyan)
                    Text("پرداخت آنلاین هنوز فعال نیست. این نسخه آزمایشی است؛ برای قابلیت‌های ابری یا رسانه‌های پولی، تا راه‌اندازی پرداخت از کاربران پول نگیر.")
                }
            },
            confirmButton = { Button(onClick = { showPackages = false }) { Text("متوجه شدم") } },
            containerColor = AriaPanel,
            titleContentColor = AriaCyan,
            textContentColor = AriaText
        )
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
