package edu.cwru.watch_bridge.presentation

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.wear.compose.material.*
import edu.cwru.watch_bridge.presentation.theme.HapticWatchTheme
import edu.cwru.watch_bridge.viewmodels.SessionState
import edu.cwru.watch_bridge.viewmodels.SessionViewModel

class MainActivity : ComponentActivity() {
    private lateinit var viewModel: SessionViewModel
    
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        setTheme(android.R.style.Theme_DeviceDefault)
        
        viewModel = SessionViewModel(applicationContext)
        
        setContent {
            HapticWatchApp(viewModel)
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
    }
}

@Composable
fun HapticWatchApp(viewModel: SessionViewModel) {
    val sessionState by viewModel.sessionState.collectAsState()
    
    HapticWatchTheme {
        Scaffold(
            timeText = { TimeText() }
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colors.background)
                    .padding(16.dp),
                contentAlignment = Alignment.Center
            ) {
                // Single button that shows IDLE or STOP based on session state
                SessionButton(sessionState, viewModel)
            }
        }
    }
}

@Composable
fun SessionButton(sessionState: SessionState, viewModel: SessionViewModel) {
    val isActive = sessionState == SessionState.ACTIVE
    val buttonText = if (isActive) "STOP" else "IDLE"
    val buttonColor = if (isActive) Color.Red else Color.DarkGray
    
    Button(
        onClick = { 
            if (isActive) {
                viewModel.stopSession()
            }
        },
        enabled = isActive,
        colors = ButtonDefaults.buttonColors(
            backgroundColor = buttonColor,
            disabledBackgroundColor = buttonColor
        ),
        modifier = Modifier.size(100.dp)
    ) {
        Text(
            text = buttonText,
            style = MaterialTheme.typography.title3,
            textAlign = TextAlign.Center
        )
    }
}