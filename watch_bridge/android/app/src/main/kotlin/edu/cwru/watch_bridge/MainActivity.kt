package edu.cwru.watch_bridge

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.annotation.NonNull
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "edu.cwru.watch_bridge/foreground_service"
    private val NOTIFICATION_PERMISSION_REQUEST_CODE = 1001
    private val TAG = "MainActivity"
    
    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        // Request notification permission on startup for Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) 
                != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    NOTIFICATION_PERMISSION_REQUEST_CODE
                )
            }
        }
        
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "startForegroundService" -> {
                    startSessionService()
                    result.success(null)
                }
                "stopForegroundService" -> {
                    stopSessionService()
                    result.success(null)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }
    
    private fun startSessionService() {
        Log.d(TAG, "startSessionService called")
        val intent = Intent(this, SessionForegroundService::class.java).apply {
            action = SessionForegroundService.ACTION_START
        }
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Log.d(TAG, "Starting foreground service (API >= O)")
            startForegroundService(intent)
        } else {
            Log.d(TAG, "Starting service (API < O)")
            startService(intent)
        }
    }
    
    private fun stopSessionService() {
        Log.d(TAG, "stopSessionService called")
        val intent = Intent(this, SessionForegroundService::class.java).apply {
            action = SessionForegroundService.ACTION_STOP
        }
        startService(intent)
    }
}
