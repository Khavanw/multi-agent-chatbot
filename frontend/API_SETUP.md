# API Setup Guide

## Environment Variables

Tạo file `.env` trong thư mục gốc của project với các biến môi trường sau:

```env
# Default Agent (Supervisor)
VITE_AGENT_SUPERVISOR_URL=https://kha-test-ai.azurewebsites.net/api/v1/agent/supervisor

# Vector DB Agent (Mega Agent)
VITE_AGENT_VECTORDB_URL=https://kha-test-ai.azurewebsites.net/api/v1/agent/chat_vectordb

# Deep Research Agent (Research Agent)
VITE_AGENT_DEEP_RESEARCH_URL=https://kha-test-ai.azurewebsites.net/api/v1/agent/deep_research

# Additional Agents
VITE_AGENT_1_URL=https://kha-test-ai.azurewebsites.net/api/v1/agent/agent1
VITE_AGENT_2_URL=https://kha-test-ai.azurewebsites.net/api/v1/agent/agent2

# Voice STT (Speech-to-Text)
VITE_VOICE_STT_URL=https://kha-test-ai.azurewebsites.net/api/v1/agent/tts_chat
```

## Agent Types

### 1. Supervisor Agent (Default)
- **Purpose**: Agent mặc định, xử lý các câu hỏi chung
- **Endpoint**: `VITE_AGENT_SUPERVISOR_URL`
- **Color**: Gold (#ffc107)

### 2. Mega Agent (Vector DB)
- **Purpose**: Tìm kiếm và hiển thị sản phẩm từ Vector Database
- **Endpoint**: `VITE_AGENT_VECTORDB_URL`
- **Color**: Blue (#007bff)
- **Features**: Product grid display, image handling

### 3. Research Agent (Deep Research)
- **Purpose**: Nghiên cứu sâu và phân tích thông tin
- **Endpoint**: `VITE_AGENT_DEEP_RESEARCH_URL`
- **Color**: Green (#28a745)
- **Features**: Structured agent/tools response format

### 4. Agent 1
- **Purpose**: Tính năng mới (có thể tùy chỉnh)
- **Endpoint**: `VITE_AGENT_1_URL`
- **Color**: Red (#dc3545)

### 5. Agent 2
- **Purpose**: Tính năng mới (có thể tùy chỉnh)
- **Endpoint**: `VITE_AGENT_2_URL`
- **Color**: Purple (#6f42c1)

### 6. Voice STT (Speech-to-Text)
- **Purpose**: Chuyển đổi giọng nói thành text
- **Endpoint**: `VITE_VOICE_STT_URL`
- **Features**: Audio recording, WAV conversion, bytes array transmission, auto-send to Supervisor Agent

## API Response Format

Tất cả các API endpoints đều sử dụng format input/output giống nhau:

### Request Format
```json
{
  "content": "Câu hỏi của người dùng"
}
```

### Voice STT Request Format
```
FormData with file_bytes field containing WAV file
```

**Backend expects:**
```python
class VoiceRequest(BaseModel):
    file_bytes: bytes = Field(..., description="bytes voices")
```

**Frontend sends:**
- Content-Type: multipart/form-data (auto-generated)
- file_bytes: WAV audio file as binary data

### Response Format
- **Streaming**: `text/stream` hoặc `application/x-ndjson`
- **JSON**: Regular JSON response với field `content`, `message`, hoặc `response`

## Setup Instructions

1. **Copy environment variables** vào file `.env`
2. **Update URLs** theo endpoint thực tế của bạn
3. **Restart development server** sau khi thay đổi environment variables
4. **Test each agent** bằng cách click vào các buttons tương ứng

## Notes

- **Default Agent**: Nếu không chọn agent nào, hệ thống sẽ sử dụng Supervisor Agent
- **Fallback URLs**: Mỗi agent có fallback URL localhost nếu environment variable không được set
- **Dynamic Routing**: API URL được chọn động dựa trên agent được chọn
- **Response Handling**: Tất cả agents đều hỗ trợ streaming và JSON responses
- **Voice STT**: Gửi file WAV dưới dạng FormData với binary file