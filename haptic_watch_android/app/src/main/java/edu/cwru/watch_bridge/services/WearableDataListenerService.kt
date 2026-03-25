package edu.cwru.watch_bridge.services

import android.content.Intent
import android.util.Log
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.WearableListenerService
import java.io.ByteArrayInputStream
import java.io.ObjectInputStream

class WearableDataListenerService : WearableListenerService() {
    
    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "============================================")
        Log.d(TAG, "WearableDataListenerService CREATED")
        Log.d(TAG, "Service is ready to receive messages")
        Log.d(TAG, "============================================")
    }
    
    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "WearableDataListenerService DESTROYED")
    }
    
    override fun onMessageReceived(messageEvent: MessageEvent) {
        super.onMessageReceived(messageEvent)
        
        Log.d(TAG, "============================================")
        Log.d(TAG, "MESSAGE RECEIVED ON WATCH!")
        Log.d(TAG, "  Path: ${messageEvent.path}")
        Log.d(TAG, "  Source node: ${messageEvent.sourceNodeId}")
        Log.d(TAG, "  Data size: ${messageEvent.data.size} bytes")
        Log.d(TAG, "============================================")
        
        Log.d(TAG, "Processing message...")
        
        try {
            // Deserialize Java HashMap from watch_connectivity
            val byteStream = ByteArrayInputStream(messageEvent.data)
            val objStream = ObjectInputStream(byteStream)
            val messageMap = objStream.readObject() as? HashMap<*, *>
            objStream.close()
            
            if (messageMap == null) {
                Log.e(TAG, "Failed to deserialize message as HashMap")
                return
            }
            
            Log.d(TAG, "  Deserialized HashMap: $messageMap")

            when (val type = messageMap["type"] as? String) {
                "command" -> handleCommand(messageMap["command"] as? String)
                "event" -> handleEvent(messageMap)
                else -> Log.w(TAG, "Unknown message type: $type")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error processing message", e)
        }
    }
    
    private fun handleCommand(command: String?) {
        when (command) {
            "start" -> {
                Log.d(TAG, "Received start command")
                // Start the foreground service
                val intent = Intent(this, edu.cwru.watch_bridge.presentation.HapticService::class.java).apply {
                    action = "ACTION_START"
                }
                startService(intent)
            }
            "stop" -> {
                Log.d(TAG, "Received stop command")
                // Stop the foreground service
                val intent = Intent(this, edu.cwru.watch_bridge.presentation.HapticService::class.java).apply {
                    action = "ACTION_STOP"
                }
                startService(intent)
            }
            else -> Log.w(TAG, "Unknown command: $command")
        }
    }
    
    private fun handleEvent(messageMap: HashMap<*, *>) {
        val intensity = (messageMap["intensity"] as? Int) ?: 128
        val duration = (messageMap["duration"] as? Int) ?: 100
        val timeBetween = (messageMap["timeBetween"] as? Int) ?: 0
        
        Log.d(TAG, "Received haptic event: intensity=$intensity, duration=$duration, timeBetween=$timeBetween")
        
        // Send event to the foreground service to execute
        val intent = Intent(this, edu.cwru.watch_bridge.presentation.HapticService::class.java).apply {
            action = "ACTION_HAPTIC_EVENT"
            putExtra("intensity", intensity)
            putExtra("duration", duration)
            putExtra("timeBetween", timeBetween)
        }
        startService(intent)
    }
    
    companion object {
        private const val TAG = "WearableListener"
    }
}
