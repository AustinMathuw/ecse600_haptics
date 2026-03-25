package edu.cwru.watch_bridge

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat

class SessionForegroundService : Service() {
    
    private var wakeLock: PowerManager.WakeLock? = null
    
    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "SessionForegroundService created")
        createNotificationChannel()
        
        // Acquire a wake lock to keep the service running
        val powerManager = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "WatchBridge::SessionWakeLock"
        )
        wakeLock?.acquire()
        Log.d(TAG, "Wake lock acquired")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "onStartCommand called with action: ${intent?.action}")
        when (intent?.action) {
            ACTION_START -> {
                try {
                    val notification = createNotification()
                    startForeground(NOTIFICATION_ID, notification)
                    Log.d(TAG, "Foreground service started with notification")
                } catch (e: Exception) {
                    Log.e(TAG, "Error starting foreground service", e)
                }
            }
            ACTION_STOP -> {
                Log.d(TAG, "Stopping foreground service")
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
        return START_STICKY
    }
    
    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
    
    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "SessionForegroundService destroyed")
        wakeLock?.let {
            if (it.isHeld) {
                it.release()
                Log.d(TAG, "Wake lock released")
            }
        }
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "WebSocket Connection",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps the WebSocket connection active in the background"
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
            .setContentTitle("Watch Bridge Active")
            .setContentText("Maintaining WebSocket connection")
            .setSmallIcon(android.R.drawable.ic_notification_overlay)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }
    
    companion object {
        private const val TAG = "ForegroundService"
        const val CHANNEL_ID = "haptic_session_channel"
        const val NOTIFICATION_ID = 1
        const val ACTION_START = "ACTION_START_SESSION"
        const val ACTION_STOP = "ACTION_STOP_SESSION"
    }
}
