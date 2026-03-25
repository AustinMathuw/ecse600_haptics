package edu.cwru.watch_bridge.services

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log

class HapticManager(private val context: Context) {

    private val vibrator: Vibrator =
        (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager).defaultVibrator

    private val supportsAmplitudeControl: Boolean = vibrator.hasAmplitudeControl()

    private val supportedPrimitives: Set<Int> = buildSet {
        val toCheck = intArrayOf(
            VibrationEffect.Composition.PRIMITIVE_LOW_TICK,
            VibrationEffect.Composition.PRIMITIVE_TICK,
            VibrationEffect.Composition.PRIMITIVE_CLICK,
            VibrationEffect.Composition.PRIMITIVE_QUICK_RISE,
            VibrationEffect.Composition.PRIMITIVE_THUD,
        )
        toCheck.zip(vibrator.arePrimitivesSupported(*toCheck).toList())
            .forEach { (primitive, supported) -> if (supported) add(primitive) }
    }

    private val handler = Handler(Looper.getMainLooper())

    // Current loop state
    private var loopStartTime: Long = 0L
    private var loopIntensity: Int = -1
    private var loopDuration: Int = -1
    private var loopGap: Int = -1

    // Pending update to apply at the next gap
    private var pendingIntensity: Int = -1
    private var pendingDuration: Int = -1
    private var pendingGap: Int = -1

    // Runs every 100ms while a loop is active; applies any pending update when we're in the gap
    private val intervalRunnable = object : Runnable {
        override fun run() {
            if (loopDuration == -1) return  // loop stopped, let it die

            if (pendingIntensity != -1) {
                val period = (loopDuration + loopGap).toLong()
                val elapsed = (System.currentTimeMillis() - loopStartTime) % period

                if (elapsed >= loopDuration) {
                    applyLoop(pendingIntensity, pendingDuration, pendingGap)
                    pendingIntensity = -1
                }
            }

            handler.postDelayed(this, 100)
        }
    }

    init {
        Log.d(TAG, "HapticManager initialized")
        Log.d(TAG, "  Amplitude control: $supportsAmplitudeControl")
        Log.d(TAG, "  Supported primitives: ${supportedPrimitives.map(::primitiveToString)}")
    }

    fun executeHapticPattern(intensity: Int, duration: Int, gap: Int, mode: String = "oneshot") {
        if (!vibrator.hasVibrator()) {
            Log.w(TAG, "Device does not have a vibrator")
            return
        }

        val clampedIntensity = intensity.coerceIn(0, 255)

        if (clampedIntensity == 0) {
            handler.removeCallbacks(intervalRunnable)
            pendingIntensity = -1
            clearLoopState()
            vibrator.cancel()
            Log.d(TAG, "Stopping haptic feedback (intensity=0)")
            return
        }

        if (mode == "loop") {
            playLoop(clampedIntensity, duration, gap)
        } else {
            playOneshot(clampedIntensity, duration)
        }
    }

    private fun playLoop(intensity: Int, duration: Int, gap: Int) {
        if (intensity == loopIntensity && duration == loopDuration && gap == loopGap) return

        if (loopDuration == -1) {
            // No loop running yet — start immediately and kick off the interval
            applyLoop(intensity, duration, gap)
            handler.postDelayed(intervalRunnable, 100)
            return
        }

        // Loop already running — stage the update; intervalRunnable will apply it at the next gap
        pendingIntensity = intensity
        pendingDuration = duration
        pendingGap = gap
    }

    private fun applyLoop(intensity: Int, duration: Int, gap: Int) {
        val timings = if (gap > 0) longArrayOf(duration.toLong(), gap.toLong()) else longArrayOf(duration.toLong())
        val amplitudes = if (gap > 0) intArrayOf(intensity, 0) else intArrayOf(intensity)

        loopIntensity = intensity
        loopDuration = duration
        loopGap = gap
        loopStartTime = System.currentTimeMillis()

        vibrator.cancel()
        vibrator.vibrate(VibrationEffect.createWaveform(timings, amplitudes, 0))
        Log.d(TAG, "Applied loop: intensity=$intensity, duration=${duration}ms, gap=${gap}ms")
    }

    private fun clearLoopState() {
        loopIntensity = -1
        loopDuration = -1
        loopGap = -1
    }

    private fun playOneshot(intensity: Int, duration: Int) {
        val primitive = primitiveForDuration(duration)

        if (primitive != null && primitive in supportedPrimitives) {
            // Composition primitives are hardware-tuned by the manufacturer for clean, clear haptics.
            // Scale maps 0-255 intensity → 0.01-1.0 (0.0 in the API means minimum perceivable, not off).
            val scale = (intensity / 255f).coerceAtLeast(0.01f)
            val effect = VibrationEffect.startComposition()
                .addPrimitive(primitive, scale)
                .compose()
            vibrator.vibrate(effect)
            Log.d(TAG, "Oneshot composition: primitive=${primitiveToString(primitive)}, scale=%.2f".format(scale))
        } else {
            val effect = VibrationEffect.createOneShot(duration.toLong(), intensity)
            vibrator.vibrate(effect)
            Log.d(TAG, "Oneshot fallback: intensity=$intensity, duration=${duration}ms")
        }
    }

    private fun primitiveForDuration(duration: Int): Int? = when {
        duration <= 30  -> VibrationEffect.Composition.PRIMITIVE_LOW_TICK
        duration <= 75  -> VibrationEffect.Composition.PRIMITIVE_TICK
        duration <= 150 -> VibrationEffect.Composition.PRIMITIVE_CLICK
        duration <= 300 -> VibrationEffect.Composition.PRIMITIVE_QUICK_RISE
        else            -> VibrationEffect.Composition.PRIMITIVE_THUD
    }

    private fun primitiveToString(primitive: Int): String = when (primitive) {
        VibrationEffect.Composition.PRIMITIVE_LOW_TICK   -> "LOW_TICK"
        VibrationEffect.Composition.PRIMITIVE_TICK       -> "TICK"
        VibrationEffect.Composition.PRIMITIVE_CLICK      -> "CLICK"
        VibrationEffect.Composition.PRIMITIVE_QUICK_RISE -> "QUICK_RISE"
        VibrationEffect.Composition.PRIMITIVE_THUD       -> "THUD"
        else -> "UNKNOWN($primitive)"
    }

    fun cancelHaptic() {
        try {
            handler.removeCallbacks(intervalRunnable)
            pendingIntensity = -1
            clearLoopState()
            vibrator.cancel()
            Log.d(TAG, "Cancelled haptic feedback")
        } catch (e: Exception) {
            Log.e(TAG, "Error cancelling haptic", e)
        }
    }

    companion object {
        private const val TAG = "HapticManager"
    }
}