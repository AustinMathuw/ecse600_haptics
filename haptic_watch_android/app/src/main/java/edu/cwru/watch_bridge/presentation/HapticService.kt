package edu.cwru.watch_bridge.presentation

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import edu.cwru.watch_bridge.R
import edu.cwru.watch_bridge.services.HapticManager

class HapticService : Service() {
    
    private lateinit var hapticManager: HapticManager
    private var isSessionActive = false
    
    override fun onCreate() {
        super.onCreate()
        hapticManager = HapticManager(this)
        createNotificationChannel()
        Log.d(TAG, "HapticService created")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                Log.d(TAG, "Starting haptic session")
                startForegroundService()
                isSessionActive = true
                // Broadcast session state change
                sendBroadcast(Intent(ACTION_SESSION_STATE_CHANGED).apply {
                    putExtra("isActive", true)
                })
            }
            ACTION_STOP -> {
                Log.d(TAG, "Stopping haptic session")
                isSessionActive = false
                hapticManager.cancelHaptic()
                // Broadcast session state change
                sendBroadcast(Intent(ACTION_SESSION_STATE_CHANGED).apply {
                    putExtra("isActive", false)
                })
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
            ACTION_HAPTIC_EVENT -> {
                val intensity = intent.getIntExtra("intensity", 128)
                val duration = intent.getIntExtra("duration", 100)
                val gap = intent.getIntExtra("timeBetween", 0)
                val mode = intent.getStringExtra("mode") ?: "oneshot"
                
                // Auto-start session if not active for standalone haptic events
                if (!isSessionActive) {
                    Log.d(TAG, "Auto-starting session for haptic event")
                    startForegroundService()
                    isSessionActive = true
                    sendBroadcast(Intent(ACTION_SESSION_STATE_CHANGED).apply {
                        putExtra("isActive", true)
                    })
                }
                
                Log.d(TAG, "Executing haptic event: mode=$mode, intensity=$intensity, duration=$duration, gap=$gap")
                hapticManager.executeHapticPattern(intensity, duration, gap, mode)
            }
        }
        
        return START_STICKY
    }
    
    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
    
    override fun onDestroy() {
        super.onDestroy()
        hapticManager.cancelHaptic()
        Log.d(TAG, "HapticService destroyed")
    }
    
    private fun startForegroundService() {
        val notification = createNotification()
        startForeground(NOTIFICATION_ID, notification)
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Haptic Session",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Haptic feedback session notifications"
                setShowBadge(false)
            }
            
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    private fun createNotification(): Notification {
        val notificationIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            notificationIntent,
            PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Haptic Session Active")
            .setContentText("Listening for haptic events")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }
    
    companion object {
        private const val TAG = "HapticService"
        private const val NOTIFICATION_ID = 1
        private const val CHANNEL_ID = "haptic_service_channel"
        
        const val ACTION_START = "ACTION_START"
        const val ACTION_STOP = "ACTION_STOP"
        const val ACTION_HAPTIC_EVENT = "ACTION_HAPTIC_EVENT"
        const val ACTION_SESSION_STATE_CHANGED = "edu.cwru.watch_bridge.SESSION_STATE_CHANGED"
    }
}
