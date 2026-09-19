package com.miladdeljoui.aria

import android.content.Context
import android.content.SharedPreferences
import java.security.MessageDigest

/**
 * قفل مالک: رمز (PIN) + عبارت صوتی که خود کاربر تنظیم می‌کند.
 * داده فقط روی خود دستگاه ذخیره می‌شود.
 */
class OwnerLock(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("aria_owner_lock", Context.MODE_PRIVATE)

    fun isConfigured(): Boolean {
        return prefs.contains("pin_hash") && prefs.contains("voice_phrase")
    }

    fun setup(pin: String, voicePhrase: String): Boolean {
        val cleanPin = pin.trim()
        val cleanPhrase = normalizePhrase(voicePhrase)
        if (cleanPin.length < 4) return false
        if (cleanPhrase.length < 3) return false

        prefs.edit()
            .putString("pin_hash", sha256(cleanPin))
            .putString("voice_phrase", cleanPhrase)
            .apply()
        return true
    }

    fun unlockWithPin(pin: String): Boolean {
        val stored = prefs.getString("pin_hash", null) ?: return false
        return sha256(pin.trim()) == stored
    }

    fun unlockWithVoice(spoken: String): Boolean {
        val expected = prefs.getString("voice_phrase", null) ?: return false
        return normalizePhrase(spoken) == expected
    }

    fun voicePhraseHint(): String {
        val phrase = prefs.getString("voice_phrase", "") ?: ""
        if (phrase.isBlank()) return ""
        // فقط اولین کلمه را برای راهنما نشان بده
        return phrase.split(" ").firstOrNull()?.take(2)?.plus("…") ?: "…"
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    private fun normalizePhrase(text: String): String {
        return text.trim()
            .lowercase()
            .replace(Regex("\\s+"), " ")
            .replace(Regex("[^\\p{L}\\p{N} ]"), "")
    }

    private fun sha256(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val bytes = digest.digest(value.toByteArray(Charsets.UTF_8))
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
