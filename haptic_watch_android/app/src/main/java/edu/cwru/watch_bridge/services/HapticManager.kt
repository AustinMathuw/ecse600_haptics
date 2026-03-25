package edu.cwru.watch_bridge.services

import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
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

    private val handler = Handler(Looper.getMainLooper())
    private var isLooping = false
    
    // Dynamic parameters
    private var currentIntensity = 128
    private var currentDuration = 150L
    private var currentGap = 500L

    private val vibrationRunnable = object : Runnable {
        override fun run() {
            Log.d(TAG, "Runnable executing: isLooping=$isLooping, duration=$currentDuration, gap=$currentGap")
            if (!isLooping) return

            try {
                // Trigger the pulse with current parameters
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    val effect = VibrationEffect.createOneShot(currentDuration, currentIntensity)
                    vibrator.vibrate(effect)
                } else {
                    @Suppress("DEPRECATION")
                    vibrator.vibrate(currentDuration)
                }

                // Schedule next pulse after (duration + gap)
                handler.postDelayed(this, currentDuration + currentGap)
            } catch (e: Exception) {
                Log.e(TAG, "Error in vibration loop", e)
            }
        }
    }

    /**
     * Execute a haptic pattern with the given parameters.
     * Loop mode uses recursive Handler scheduling for dynamic gap control.
     * 
     * @param intensity 0-255 vibration intensity
     * @param duration duration of vibration in milliseconds
     * @param gap time between vibrations in milliseconds
     * @param mode "loop" for continuous repeat, "oneshot" for single pattern
     */
    fun executeHapticPattern(intensity: Int, duration: Int, gap: Int, mode: String = "oneshot") {
        if (!vibrator.hasVibrator()) {
            Log.w(TAG, "Device does not have a vibrator")
            return
        }

        val clampedIntensity = intensity.coerceIn(0, 255)
        
        // Handle stop signal (intensity 0)
        if (clampedIntensity == 0) {
            stopLoop()
            vibrator.cancel()
            Log.d(TAG, "Stopping haptic feedback (intensity=0)")
            return
        }

        if (mode == "loop") {
            // Update parameters
            currentIntensity = clampedIntensity
            currentDuration = duration.toLong()
            currentGap = gap.toLong()

            if (!isLooping) {
                isLooping = true
                handler.post(vibrationRunnable)
                Log.d(TAG, "Started loop: intensity=$clampedIntensity, duration=$duration, gap=$gap")
            } else {
                // Just update parameters, let the existing loop continue with new values
                Log.d(TAG, "Updated loop parameters: intensity=$clampedIntensity, duration=$duration, gap=$gap")
                // The next scheduled callback will use the updated currentIntensity, currentDuration, currentGap
            }
        } else {
            // Oneshot mode
            stopLoop()
            
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    val effect = VibrationEffect.createOneShot(duration.toLong(), clampedIntensity)
                    vibrator.vibrate(effect)
                    Log.d(TAG, "Executed oneshot: intensity=$clampedIntensity, duration=$duration")
                } else {
                    @Suppress("DEPRECATION")
                    vibrator.vibrate(duration.toLong())
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error executing oneshot", e)
            }
        }
    }

    private fun stopLoop() {
        if (isLooping) {
            isLooping = false
            handler.removeCallbacks(vibrationRunnable)
            Log.d(TAG, "Stopped vibration loop")
        }
    }

    /**
     * Cancel any ongoing vibration
     */
    fun cancelHaptic() {
        try {
            stopLoop()
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