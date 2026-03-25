package edu.cwru.watch_bridge.services

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log

class HapticManager(private val context: Context) {
    private val vibrator: Vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
        vibratorManager.defaultVibrator
    } else {
        @Suppress("DEPRECATION")
        context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
    }

    /**
     * Execute a haptic pattern with the given parameters
     * @param intensity 0-255 vibration intensity
     * @param duration duration of vibration in milliseconds
     * @param timeBetween time between vibrations in milliseconds (for patterns)
     */
    fun executeHapticPattern(intensity: Int, duration: Int, timeBetween: Int) {
        if (!vibrator.hasVibrator()) {
            Log.w(TAG, "Device does not have a vibrator")
            return
        }

        val clampedIntensity = intensity.coerceIn(0, 255)

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                // Use VibrationEffect for newer Android versions
                if (timeBetween > 0) {
                    // Create a repeating pattern: vibrate -> pause -> repeat
                    val timings = longArrayOf(0, duration.toLong(), timeBetween.toLong())
                    val amplitudes = intArrayOf(0, clampedIntensity, 0)
                    
                    val effect = VibrationEffect.createWaveform(timings, amplitudes, -1) // -1 means no repeat
                    vibrator.vibrate(effect)
                } else {
                    // Single vibration
                    val effect = VibrationEffect.createOneShot(duration.toLong(), clampedIntensity)
                    vibrator.vibrate(effect)
                }
            } else {
                // Fallback for older Android versions
                @Suppress("DEPRECATION")
                if (timeBetween > 0) {
                    val pattern = longArrayOf(0, duration.toLong(), timeBetween.toLong())
                    vibrator.vibrate(pattern, -1)
                } else {
                    vibrator.vibrate(duration.toLong())
                }
            }
            
            Log.d(TAG, "Executed haptic pattern: intensity=$clampedIntensity, duration=$duration, timeBetween=$timeBetween")
        } catch (e: Exception) {
            Log.e(TAG, "Error executing haptic pattern", e)
        }
    }

    /**
     * Cancel any ongoing vibration
     */
    fun cancelHaptic() {
        try {
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
