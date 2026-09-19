package com.miladdeljoui.aria

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer

class VoiceController(
    context: Context,
    private val onText: (String) -> Unit,
    private val onState: (String) -> Unit
) {
    private val recognizer: SpeechRecognizer? =
        if (SpeechRecognizer.isRecognitionAvailable(context)) {
            SpeechRecognizer.createSpeechRecognizer(context)
        } else {
            null
        }

    init {
        recognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                onState("در حال شنیدن…")
            }

            override fun onBeginningOfSpeech() {
                onState("صدای تو را می‌شنوم")
            }

            override fun onRmsChanged(rmsdB: Float) = Unit

            override fun onBufferReceived(buffer: ByteArray?) = Unit

            override fun onEndOfSpeech() {
                onState("در حال پردازش…")
            }

            override fun onError(error: Int) {
                onState("تشخیص صدا متوقف شد")
            }

            override fun onResults(results: Bundle?) {
                val text = results
                    ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    ?.firstOrNull()
                    ?.trim()

                if (!text.isNullOrBlank()) {
                    onText(text)
                    onState("آماده")
                } else {
                    onState("صدایی دریافت نشد")
                }
            }

            override fun onPartialResults(partialResults: Bundle?) = Unit

            override fun onEvent(eventType: Int, params: Bundle?) = Unit
        })
    }

    fun start() {
        if (recognizer == null) {
            onState("سرویس تشخیص صدا در این دستگاه در دسترس نیست")
            return
        }

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
            )
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "fa-IR")
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "fa-IR")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        }

        recognizer.startListening(intent)
    }

    fun destroy() {
        recognizer?.destroy()
    }
}
