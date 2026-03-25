package edu.cwru.watch_bridge.viewmodels

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.android.gms.wearable.MessageClient
import com.google.android.gms.wearable.Wearable
import edu.cwru.watch_bridge.presentation.HapticService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.io.ByteArrayOutputStream
import java.io.ObjectOutputStream

enum class SessionState {
    IDLE,
    ACTIVE,
    ERROR
}

class SessionViewModel(private val context: Context) : ViewModel() {
    
    private val _sessionState = MutableStateFlow(SessionState.IDLE)
    val sessionState: StateFlow<SessionState> = _sessionState.asStateFlow()
    
    private val messageClient: MessageClient = Wearable.getMessageClient(context)
    
    private val sessionStateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val isActive = intent?.getBooleanExtra("isActive", false) ?: false
            _sessionState.value = if (isActive) SessionState.ACTIVE else SessionState.IDLE
            Log.d(TAG, "Session state updated: ${_sessionState.value}")
        }
    }
    
    init {
        // Register broadcast receiver for session state changes
        val filter = IntentFilter(HapticService.ACTION_SESSION_STATE_CHANGED)
        context.registerReceiver(sessionStateReceiver, filter, Context.RECEIVER_EXPORTED)
    }
    
    fun stopSession() {
        viewModelScope.launch {
            try {
                // Stop the local foreground service
                val intent = Intent(context, HapticService::class.java).apply {
                    action = HapticService.ACTION_STOP
                }
                context.startService(intent)
                
                // Send stop command to phone
                sendStopCommandToPhone()
                
                _sessionState.value = SessionState.IDLE
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping session", e)
                _sessionState.value = SessionState.ERROR
            }
        }
    }
    
    private suspend fun sendStopCommandToPhone() {
        try {
            // Get connected nodes (phones)
            val nodeClient = Wearable.getNodeClient(context)
            val nodes = nodeClient.connectedNodes.await()
            
            if (nodes.isEmpty()) {
                Log.w(TAG, "No connected nodes found")
                return
            }
            
            // Create HashMap and serialize it (same format as watch_connectivity sends)
            val message = hashMapOf<String, Any>(
                "type" to "command",
                "command" to "stop"
            )
            
            val byteStream = ByteArrayOutputStream()
            val objStream = ObjectOutputStream(byteStream)
            objStream.writeObject(message)
            objStream.close()
            val messageBytes = byteStream.toByteArray()
            
            // Send message to all connected nodes
            for (node in nodes) {
                messageClient.sendMessage(node.id, "watch_connectivity", messageBytes).await()
                Log.d(TAG, "Sent stop command to phone: ${node.displayName}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error sending stop command to phone", e)
        }
    }
    
    override fun onCleared() {
        super.onCleared()
        try {
            context.unregisterReceiver(sessionStateReceiver)
        } catch (e: Exception) {
            Log.e(TAG, "Error unregistering receiver", e)
        }
    }
    
    companion object {
        private const val TAG = "SessionViewModel"
    }
}
