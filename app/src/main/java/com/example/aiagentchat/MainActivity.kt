package com.example.aiagentchat

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.util.Base64
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.UUID
import java.util.concurrent.TimeUnit

/**
 * Model representing an AI Agent configuration.
 */
data class AiAgent(
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val provider: String, // "OPENAI_COMPATIBLE" or "GEMINI"
    val baseUrl: String,
    val apiKey: String,
    val modelName: String,
    val systemPrompt: String
)

/**
 * Model representing a chat message with optional base64 image payload.
 */
data class ChatMessage(
    val role: String, // "user" or "assistant"
    val content: String,
    val imageBase64: String? = null
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
                    Surface(
                        modifier = Modifier.fillMaxSize(),
                        color = MaterialTheme.colorScheme.background
                    ) {
                        AgentChatApp()
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AgentChatApp() {
    val context = LocalContext.current
    val clipboardManager = LocalClipboardManager.current
    val scope = rememberCoroutineScope()
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)

    var agents by remember { mutableStateOf(loadAgents(context)) }
    var selectedAgent by remember { mutableStateOf(agents.firstOrNull()) }
    var currentMessages by remember { mutableStateOf<List<ChatMessage>>(emptyList()) }

    var inputText by remember { mutableStateOf("") }
    var attachedImageBase64 by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(false) }

    var showAgentDialog by remember { mutableStateOf(false) }
    var agentToEdit by remember { mutableStateOf<AiAgent?>(null) }

    val listState = rememberLazyListState()

    // Load conversation history whenever active agent changes
    LaunchedEffect(selectedAgent?.id) {
        currentMessages = selectedAgent?.let { loadChatHistory(context, it.id) } ?: emptyList()
        if (currentMessages.isNotEmpty()) {
            listState.scrollToItem(currentMessages.size - 1)
        }
    }

    // Gallery image picker launcher
    val imagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            scope.launch {
                attachedImageBase64 = encodeUriToBase64(context, it)
            }
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(modifier = Modifier.width(300.dp)) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("لیست ایجنت‌ها", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    IconButton(onClick = {
                        agentToEdit = null
                        showAgentDialog = true
                    }) {
                        Icon(Icons.Default.Add, contentDescription = "افزودن ایجنت")
                    }
                }
                HorizontalDivider()
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(agents) { agent ->
                        NavigationDrawerItem(
                            label = {
                                Column {
                                    Text(agent.name, fontWeight = FontWeight.SemiBold)
                                    Text(agent.modelName, fontSize = 12.sp, color = Color.Gray)
                                }
                            },
                            selected = selectedAgent?.id == agent.id,
                            onClick = {
                                selectedAgent = agent
                                scope.launch { drawerState.close() }
                            },
                            badge = {
                                Row {
                                    IconButton(onClick = {
                                        agentToEdit = agent
                                        showAgentDialog = true
                                    }) {
                                        Icon(Icons.Default.Edit, contentDescription = "ویرایش")
                                    }
                                    IconButton(onClick = {
                                        deleteChatHistory(context, agent.id)
                                        agents = agents.filter { it.id != agent.id }
                                        saveAgents(context, agents)
                                        if (selectedAgent?.id == agent.id) {
                                            selectedAgent = agents.firstOrNull()
                                        }
                                    }) {
                                        Icon(Icons.Default.Delete, contentDescription = "حذف")
                                    }
                                }
                            },
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        )
                    }
                }
            }
        }
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = {
                        Column {
                            Text(selectedAgent?.name ?: "ایجنتی انتخاب نشده")
                            if (selectedAgent != null) {
                                Text(
                                    text = "${selectedAgent!!.provider} | ${selectedAgent!!.modelName}",
                                    fontSize = 11.sp,
                                    color = Color.LightGray
                                )
                            }
                        }
                    },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Default.Menu, contentDescription = "منو")
                        }
                    },
                    actions = {
                        if (selectedAgent != null) {
                            IconButton(onClick = {
                                deleteChatHistory(context, selectedAgent!!.id)
                                currentMessages = emptyList()
                            }) {
                                Icon(Icons.Default.DeleteSweep, contentDescription = "پاکسازی چت")
                            }
                        }
                    }
                )
            }
        ) { paddingValues ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
            ) {
                if (selectedAgent == null) {
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth(),
                        contentAlignment = Alignment.Center
                    ) {
                        Button(onClick = {
                            agentToEdit = null
                            showAgentDialog = true
                        }) {
                            Text("ساخت اولین ایجنت")
                        }
                    }
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth()
                            .padding(horizontal = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                        contentPadding = PaddingValues(vertical = 12.dp)
                    ) {
                        items(currentMessages) { msg ->
                            val isUser = msg.role == "user"
                            Box(
                                modifier = Modifier.fillMaxWidth(),
                                contentAlignment = if (isUser) Alignment.CenterStart else Alignment.CenterEnd
                            ) {
                                Column(
                                    modifier = Modifier
                                        .widthIn(max = 310.dp)
                                        .background(
                                            color = if (isUser) MaterialTheme.colorScheme.primaryContainer
                                            else MaterialTheme.colorScheme.secondaryContainer,
                                            shape = RoundedCornerShape(14.dp)
                                        )
                                        .clickable {
                                            clipboardManager.setText(AnnotatedString(msg.content))
                                            Toast.makeText(context, "متن کپی شد", Toast.LENGTH_SHORT).show()
                                        }
                                        .padding(12.dp)
                                ) {
                                    if (msg.imageBase64 != null) {
                                        val bmp = remember(msg.imageBase64) {
                                            decodeBase64ToBitmap(msg.imageBase64)
                                        }
                                        if (bmp != null) {
                                            Image(
                                                bitmap = bmp.asImageBitmap(),
                                                contentDescription = "تصویر پیوست",
                                                modifier = Modifier
                                                    .fillMaxWidth()
                                                    .heightIn(max = 200.dp)
                                                    .clip(RoundedCornerShape(8.dp)),
                                                contentScale = ContentScale.Crop
                                            )
                                            Spacer(modifier = Modifier.height(6.dp))
                                        }
                                    }
                                    Text(
                                        text = msg.content,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                            }
                        }
                        if (isLoading) {
                            item {
                                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                            }
                        }
                    }

                    // Attached image preview before sending
                    if (attachedImageBase64 != null) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 12.dp, vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            val previewBmp = remember(attachedImageBase64) {
                                decodeBase64ToBitmap(attachedImageBase64!!)
                            }
                            if (previewBmp != null) {
                                Image(
                                    bitmap = previewBmp.asImageBitmap(),
                                    contentDescription = "پیش‌نمایش",
                                    modifier = Modifier
                                        .size(60.dp)
                                        .clip(RoundedCornerShape(8.dp)),
                                    contentScale = ContentScale.Crop
                                )
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("تصویر آماده ارسال", fontSize = 13.sp, modifier = Modifier.weight(1f))
                            IconButton(onClick = { attachedImageBase64 = null }) {
                                Icon(Icons.Default.Close, contentDescription = "حذف تصویر")
                            }
                        }
                    }

                    // Input bar for typing and attachment
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        IconButton(
                            onClick = { imagePickerLauncher.launch("image/*") },
                            enabled = !isLoading
                        ) {
                            Icon(Icons.Default.AttachFile, contentDescription = "پیوست تصویر")
                        }
                        OutlinedTextField(
                            value = inputText,
                            onValueChange = { inputText = it },
                            placeholder = { Text("پیام خود را بنویسید...") },
                            modifier = Modifier.weight(1f),
                            maxLines = 4
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        IconButton(
                            enabled = (inputText.isNotBlank() || attachedImageBase64 != null) && !isLoading,
                            onClick = {
                                val agent = selectedAgent ?: return@IconButton
                                val userText = inputText.trim().ifEmpty { "این تصویر را بررسی کن." }
                                val imgData = attachedImageBase64

                                inputText = ""
                                attachedImageBase64 = null

                                val updatedHistory = currentMessages + ChatMessage("user", userText, imgData)
                                currentMessages = updatedHistory
                                saveChatHistory(context, agent.id, updatedHistory)
                                isLoading = true

                                scope.launch {
                                    listState.animateScrollToItem(updatedHistory.size - 1)
                                    val reply = sendMessageToApi(agent, updatedHistory)
                                    val finalHistory = updatedHistory + ChatMessage("assistant", reply)
                                    currentMessages = finalHistory
                                    saveChatHistory(context, agent.id, finalHistory)
                                    isLoading = false
                                    listState.animateScrollToItem(finalHistory.size - 1)
                                }
                            }
                        ) {
                            Icon(Icons.Default.Send, contentDescription = "ارسال")
                        }
                    }
                }
            }
        }
    }

    if (showAgentDialog) {
        AgentConfigDialog(
            initialAgent = agentToEdit,
            onDismiss = { showAgentDialog = false },
            onSave = { savedAgent ->
                agents = if (agentToEdit == null) {
                    agents + savedAgent
                } else {
                    agents.map { if (it.id == savedAgent.id) savedAgent else it }
                }
                saveAgents(context, agents)
                selectedAgent = savedAgent
                showAgentDialog = false
            }
        )
    }
}

@Composable
fun AgentConfigDialog(
    initialAgent: AiAgent?,
    onDismiss: () -> Unit,
    onSave: (AiAgent) -> Unit
) {
    var name by remember { mutableStateOf(initialAgent?.name ?: "") }
    var provider by remember { mutableStateOf(initialAgent?.provider ?: "OPENAI_COMPATIBLE") }
    var baseUrl by remember {
        mutableStateOf(initialAgent?.baseUrl ?: "https://api.openai.com/v1/chat/completions")
    }
    var apiKey by remember { mutableStateOf(initialAgent?.apiKey ?: "") }
    var modelName by remember { mutableStateOf(initialAgent?.modelName ?: "gpt-4o-mini") }
    var systemPrompt by remember {
        mutableStateOf(initialAgent?.systemPrompt ?: "تو یک دستیار هوشمند و دقیق هستی.")
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (initialAgent == null) "تعریف ایجنت جدید" else "ویرایش ایجنت") },
        text = {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        label = { Text("نام ایجنت") },
                        singleLine = true
                    )
                }
                item {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(
                            selected = provider == "OPENAI_COMPATIBLE",
                            onClick = {
                                provider = "OPENAI_COMPATIBLE"
                                if (initialAgent == null) {
                                    baseUrl = "https://api.openai.com/v1/chat/completions"
                                    modelName = "gpt-4o-mini"
                                }
                            }
                        )
                        Text("OpenAI / OpenRouter", fontSize = 12.sp)
                        Spacer(modifier = Modifier.width(6.dp))
                        RadioButton(
                            selected = provider == "GEMINI",
                            onClick = {
                                provider = "GEMINI"
                                if (initialAgent == null) {
                                    baseUrl = "https://generativelanguage.googleapis.com/v1beta/models"
                                    modelName = "gemini-2.5-flash"
                                }
                            }
                        )
                        Text("Gemini", fontSize = 12.sp)
                    }
                }
                item {
                    OutlinedTextField(
                        value = baseUrl,
                        onValueChange = { baseUrl = it },
                        label = { Text("آدرس Endpoint / Base URL") },
                        singleLine = true
                    )
                }
                item {
                    OutlinedTextField(
                        value = modelName,
                        onValueChange = { modelName = it },
                        label = { Text("نام مدل (Model ID)") },
                        singleLine = true
                    )
                }
                item {
                    OutlinedTextField(
                        value = apiKey,
                        onValueChange = { apiKey = it },
                        label = { Text("کلید API") },
                        visualTransformation = PasswordVisualTransformation(),
                        singleLine = true
                    )
                }
                item {
                    OutlinedTextField(
                        value = systemPrompt,
                        onValueChange = { systemPrompt = it },
                        label = { Text("دستورالعمل سیستم (System Prompt)") },
                        minLines = 3
                    )
                }
            }
        },
        confirmButton = {
            Button(
                enabled = name.isNotBlank() && apiKey.isNotBlank() && modelName.isNotBlank(),
                onClick = {
                    onSave(
                        AiAgent(
                            id = initialAgent?.id ?: UUID.randomUUID().toString(),
                            name = name.trim(),
                            provider = provider,
                            baseUrl = baseUrl.trim(),
                            apiKey = apiKey.trim(),
                            modelName = modelName.trim(),
                            systemPrompt = systemPrompt.trim()
                        )
                    )
                }
            ) {
                Text("ذخیره")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("انصراف")
            }
        }
    )
}

/**
 * Handles network transmission to AI providers supporting text and vision attachments.
 */
suspend fun sendMessageToApi(agent: AiAgent, history: List<ChatMessage>): String {
    return withContext(Dispatchers.IO) {
        val client = OkHttpClient.Builder()
            .connectTimeout(90, TimeUnit.SECONDS)
            .readTimeout(90, TimeUnit.SECONDS)
            .build()

        try {
            val request = if (agent.provider == "GEMINI") {
                val cleanBase = agent.baseUrl.trim().trimEnd('/')
                val finalBase = if (cleanBase.endsWith("/models") || cleanBase.contains("/v1beta/models") || cleanBase.contains("/v1/models")) {
                    cleanBase
                } else {
                    "$cleanBase/v1beta/models"
                }
                val url = "$finalBase/${agent.modelName.trim()}:generateContent?key=${agent.apiKey.trim()}"
                val rootJson = JSONObject()

                if (agent.systemPrompt.isNotBlank()) {
                    val sysParts = JSONArray().put(JSONObject().put("text", agent.systemPrompt))
                    rootJson.put("systemInstruction", JSONObject().put("parts", sysParts))
                }

                val contentsArray = JSONArray()
                for (msg in history) {
                    val role = if (msg.role == "user") "user" else "model"
                    val partsArray = JSONArray()
                    partsArray.put(JSONObject().put("text", msg.content))

                    if (msg.imageBase64 != null) {
                        val inlineData = JSONObject()
                            .put("mimeType", "image/jpeg")
                            .put("data", msg.imageBase64)
                        partsArray.put(JSONObject().put("inlineData", inlineData))
                    }

                    val contentObj = JSONObject()
                        .put("role", role)
                        .put("parts", partsArray)
                    contentsArray.put(contentObj)
                }
                rootJson.put("contents", contentsArray)

                Request.Builder()
                    .url(url)
                    .post(rootJson.toString().toRequestBody("application/json".toMediaType()))
                    .build()
            } else {
                val cleanBase = agent.baseUrl.trim().trimEnd('/')
                val endpointUrl = if (cleanBase.endsWith("/chat/completions")) {
                    cleanBase
                } else if (cleanBase.endsWith("/v1")) {
                    "$cleanBase/chat/completions"
                } else {
                    cleanBase
                }

                val messagesArray = JSONArray()
                if (agent.systemPrompt.isNotBlank()) {
                    messagesArray.put(
                        JSONObject().put("role", "system").put("content", agent.systemPrompt)
                    )
                }
                for (msg in history) {
                    if (msg.imageBase64 != null && msg.role == "user") {
                        val contentArray = JSONArray()
                        contentArray.put(JSONObject().put("type", "text").put("text", msg.content))
                        val imageUrlObj = JSONObject().put(
                            "url", "data:image/jpeg;base64,${msg.imageBase64}"
                        )
                        contentArray.put(
                            JSONObject().put("type", "image_url").put("image_url", imageUrlObj)
                        )
                        messagesArray.put(
                            JSONObject().put("role", msg.role).put("content", contentArray)
                        )
                    } else {
                        messagesArray.put(
                            JSONObject().put("role", msg.role).put("content", msg.content)
                        )
                    }
                }

                val bodyJson = JSONObject()
                    .put("model", agent.modelName.trim())
                    .put("messages", messagesArray)

                Request.Builder()
                    .url(endpointUrl)
                    .addHeader("Authorization", "Bearer ${agent.apiKey.trim()}")
                    .addHeader("Content-Type", "application/json")
                    .post(bodyJson.toString().toRequestBody("application/json".toMediaType()))
                    .build()
            }

            client.newCall(request).execute().use { response ->
                val rawBody = response.body?.string() ?: ""
                if (!response.isSuccessful) {
                    return@withContext "خطای سرور (${response.code}):\n$rawBody"
                }

                val json = JSONObject(rawBody)
                if (agent.provider == "GEMINI") {
                    if (json.has("error")) {
                        val errObj = json.getJSONObject("error")
                        return@withContext "خطای جمینای: ${errObj.optString("message", rawBody)}"
                    }
                    val candidates = json.optJSONArray("candidates")
                    if (candidates != null && candidates.length() > 0) {
                        val firstCandidate = candidates.getJSONObject(0)
                        val content = firstCandidate.optJSONObject("content")
                        val parts = content?.optJSONArray("parts")
                        if (parts != null && parts.length() > 0) {
                            parts.getJSONObject(0).optString("text", "بدون پاسخ متنی")
                        } else {
                            "جمینای پاسخی برنگرداند (احتمالاً به دلیل فیلتر محتوا یا مسدودیت)."
                        }
                    } else {
                        "جمینای پاسخی تولید نکرد: $rawBody"
                    }
                } else {
                    if (json.has("error")) {
                        val errObj = json.getJSONObject("error")
                        return@withContext "خطای سرور: ${errObj.optString("message", rawBody)}"
                    }
                    val choices = json.optJSONArray("choices")
                    if (choices != null && choices.length() > 0) {
                        val message = choices.getJSONObject(0).optJSONObject("message")
                        message?.optString("content", "بدون پاسخ متنی") ?: "بدون محتوا"
                    } else {
                        "پاسخی از مدل دریافت نشد: $rawBody"
                    }
                }
            }
        } catch (e: Exception) {
            "خطا در برقراری ارتباط: ${e.localizedMessage}"
        }
    }
}

/**
 * Resizes and encodes gallery image Uri to Base64 (JPEG format).
 */
suspend fun encodeUriToBase64(context: Context, uri: Uri): String? {
    return withContext(Dispatchers.IO) {
        try {
            val inputStream = context.contentResolver.openInputStream(uri) ?: return@withContext null
            val originalBitmap = BitmapFactory.decodeStream(inputStream)
            inputStream.close()

            val maxDimension = 1024
            val ratio = minOf(
                maxDimension.toFloat() / originalBitmap.width,
                maxDimension.toFloat() / originalBitmap.height,
                1.0f
            )
            val width = (originalBitmap.width * ratio).toInt()
            val height = (originalBitmap.height * ratio).toInt()
            val resizedBitmap = Bitmap.createScaledBitmap(originalBitmap, width, height, true)

            val outputStream = ByteArrayOutputStream()
            resizedBitmap.compress(Bitmap.CompressFormat.JPEG, 80, outputStream)
            Base64.encodeToString(outputStream.toByteArray(), Base64.NO_WRAP)
        } catch (_: Exception) {
            null
        }
    }
}

fun decodeBase64ToBitmap(base64Str: String): Bitmap? {
    return try {
        val bytes = Base64.decode(base64Str, Base64.DEFAULT)
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    } catch (_: Exception) {
        null
    }
}

/**
 * Persistent storage functions for Agents.
 */
fun saveAgents(context: Context, agents: List<AiAgent>) {
    val file = File(context.filesDir, "agents_data.json")
    val array = JSONArray()
    agents.forEach { a ->
        array.put(JSONObject().apply {
            put("id", a.id)
            put("name", a.name)
            put("provider", a.provider)
            put("baseUrl", a.baseUrl)
            put("apiKey", a.apiKey)
            put("modelName", a.modelName)
            put("systemPrompt", a.systemPrompt)
        })
    }
    file.writeText(array.toString())
}

fun loadAgents(context: Context): List<AiAgent> {
    val file = File(context.filesDir, "agents_data.json")
    if (!file.exists()) return emptyList()
    val list = mutableListOf<AiAgent>()
    try {
        val array = JSONArray(file.readText())
        for (i in 0 until array.length()) {
            val obj = array.getJSONObject(i)
            list.add(
                AiAgent(
                    id = obj.getString("id"),
                    name = obj.getString("name"),
                    provider = obj.getString("provider"),
                    baseUrl = obj.getString("baseUrl"),
                    apiKey = obj.getString("apiKey"),
                    modelName = obj.getString("modelName"),
                    systemPrompt = obj.getString("systemPrompt")
                )
            )
        }
    } catch (_: Exception) {}
    return list
}

/**
 * Persistent storage functions for per-agent conversation histories.
 */
fun saveChatHistory(context: Context, agentId: String, messages: List<ChatMessage>) {
    val file = File(context.filesDir, "chat_$agentId.json")
    val array = JSONArray()
    messages.forEach { m ->
        array.put(JSONObject().apply {
            put("role", m.role)
            put("content", m.content)
            if (m.imageBase64 != null) put("imageBase64", m.imageBase64)
        })
    }
    file.writeText(array.toString())
}

fun loadChatHistory(context: Context, agentId: String): List<ChatMessage> {
    val file = File(context.filesDir, "chat_$agentId.json")
    if (!file.exists()) return emptyList()
    val list = mutableListOf<ChatMessage>()
    try {
        val array = JSONArray(file.readText())
        for (i in 0 until array.length()) {
            val obj = array.getJSONObject(i)
            list.add(
                ChatMessage(
                    role = obj.getString("role"),
                    content = obj.getString("content"),
                    imageBase64 = if (obj.has("imageBase64")) obj.getString("imageBase64") else null
                )
            )
        }
    } catch (_: Exception) {}
    return list
}

fun deleteChatHistory(context: Context, agentId: String) {
    val file = File(context.filesDir, "chat_$agentId.json")
    if (file.exists()) file.delete()
}
