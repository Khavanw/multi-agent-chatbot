import { useEffect, useLayoutEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import './Home.css';

interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: Date;
  sessionId?: string; // Thêm sessionId để nhóm các message liên tiếp
  isStreaming?: boolean; // Đánh dấu message đang streaming
  agentType?: AgentType; // Thêm agentType để lưu trữ loại agent
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
}

type AgentType = 'supervisor' | 'vectordb' | 'deep_research' | 'agent1' | 'agent2';

const Home = () => {
  const [currentConversation, setCurrentConversation] = useState<Conversation>({
    id: generateConversationId(),
    title: "Cuộc trò chuyện mới",
    messages: []
  });
  const [selectedAgent, setSelectedAgent] = useState<AgentType>('supervisor'); // Mặc định là supervisor
  const [inputValue, setInputValue] = useState('');
  const [chatHistory, setChatHistory] = useState<Conversation[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentStreamingMessageId, setCurrentStreamingMessageId] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null); // Thêm sessionId hiện tại
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [audioChunks, setAudioChunks] = useState<Blob[]>([]);
  
  // Simple refs
  const sidebarRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const lastMessageRef = useRef<HTMLDivElement>(null);

  function generateConversationId() {
    return 'conv-' + Date.now();
  }

  // Optimized scroll to bottom function for mobile
  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    if (chatContainerRef.current) {
      const container = chatContainerRef.current;
      
      // Use requestAnimationFrame for better performance on mobile
      requestAnimationFrame(() => {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: behavior
        });
      });
    }
  };

  // Force scroll to bottom immediately with mobile optimization
  const scrollToBottomImmediate = () => {
    if (chatContainerRef.current) {
      const container = chatContainerRef.current;
      // Use scrollTop for immediate scroll without animation
      container.scrollTop = container.scrollHeight;
    }
  };

  // Mobile-optimized scroll with debouncing
  const debouncedScrollToBottom = useRef<NodeJS.Timeout | null>(null);
  const mobileScrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    if (debouncedScrollToBottom.current) {
      clearTimeout(debouncedScrollToBottom.current);
    }
    
    debouncedScrollToBottom.current = setTimeout(() => {
      scrollToBottom(behavior);
    }, 50); // Small delay to batch scroll operations
  };

  // Load chat history
  useEffect(() => {
    try {
      const savedHistory = localStorage.getItem("chatHistory");
      if (savedHistory) {
        const parsedHistory = JSON.parse(savedHistory);
        if (Array.isArray(parsedHistory)) {
          setChatHistory(parsedHistory);
        } else {
          localStorage.removeItem("chatHistory");
          setChatHistory([]);
        }
      }
    } catch (error) {
      console.error("Error loading chat history:", error);
      localStorage.removeItem("chatHistory");
      setChatHistory([]);
    }
  }, []);

  // Optimized auto-scroll with better performance for mobile
  useLayoutEffect(() => {
    if (lastMessageRef.current && chatContainerRef.current) {
      // Use immediate scroll for better mobile performance
      scrollToBottomImmediate();
    }
  }, [currentConversation.messages]);

  // Enhanced scroll for typing indicator with mobile optimization
  useEffect(() => {
    if (isTyping && chatContainerRef.current) {
      // Use debounced scroll for typing indicator
      mobileScrollToBottom('smooth');
    }
  }, [isTyping]);

  // Smart scroll for long content with mobile optimization
  useEffect(() => {
    if (currentConversation.messages.length > 0) {
      const lastMessage = currentConversation.messages[currentConversation.messages.length - 1];
      if (lastMessage && lastMessage.role === 'bot') {
        // Determine delay based on content complexity and device
        const isMobile = window.innerWidth <= 768;
        const hasImages = lastMessage.content.includes('![') || lastMessage.content.includes('http');
        const isLongContent = lastMessage.content.length > 1000;
        const isStreaming = lastMessage.isStreaming;
        
        // Shorter delays for mobile
        const delay = isMobile 
          ? (isStreaming ? 100 : (hasImages ? 300 : (isLongContent ? 200 : 100)))
          : (isStreaming ? 200 : (hasImages ? 500 : (isLongContent ? 300 : 150)));
        
        const timeoutId = setTimeout(() => {
          if (chatContainerRef.current) {
            mobileScrollToBottom('smooth');
          }
        }, delay);
        
        return () => clearTimeout(timeoutId);
      }
    }
  }, [currentConversation.messages]);

  // Mobile-optimized image loading
  const handleImageLoad = (event: Event) => {
    const img = event.target as HTMLImageElement;
    const container = img.closest('.image-container, .product-image-wrapper');
    
    if (container) {
      container.classList.add('image-loaded');
      
      // Mobile-optimized scroll after image load
      const isMobile = window.innerWidth <= 768;
      if (isMobile) {
        // Use immediate scroll for mobile
        setTimeout(() => {
          scrollToBottomImmediate();
        }, 50);
      } else {
        // Use smooth scroll for desktop
        requestAnimationFrame(() => {
          scrollToBottom('smooth');
        });
      }
    }
  };

  // Mobile-optimized image error handling
  const handleImageError = (event: Event) => {
    const img = event.target as HTMLImageElement;
    const container = img.closest('.image-container, .product-image-wrapper');
    
    if (container) {
      img.style.display = 'none';
      container.classList.add('image-error');
    }
  };

  // Global image load handler with mobile optimization
  useEffect(() => {
    // Use event delegation for better performance on mobile
    const container = chatContainerRef.current;
    if (container) {
      container.addEventListener('load', handleImageLoad, true);
      container.addEventListener('error', handleImageError, true);
      
      return () => {
        container.removeEventListener('load', handleImageLoad, true);
        container.removeEventListener('error', handleImageError, true);
      };
    }
  }, []);

  // Auto-save conversation
  useEffect(() => {
    if (currentConversation.messages.length > 0) {
      const existingIndex = chatHistory.findIndex(conv => conv.id === currentConversation.id);
      
      if (existingIndex !== -1) {
        const updatedHistory = [...chatHistory];
        updatedHistory[existingIndex] = {
          ...currentConversation,
          title: currentConversation.messages[0]?.content || "Cuộc trò chuyện mới"
        };
        setChatHistory(updatedHistory);
        
        try {
          localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));
        } catch (error) {
          console.error("Error auto-saving chat history:", error);
        }
      }
    }
  }, [currentConversation.messages, currentConversation.id, chatHistory]);

  // Close sidebar when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
        setIsSidebarOpen(false);
      }
    };

    if (isSidebarOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isSidebarOpen]);

  // Close sidebar on escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsSidebarOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const closeSidebar = () => {
    setIsSidebarOpen(false);
  };

  const sendMessage = async (customText?: string) => {
    const textToSend = customText || inputValue.trim();
    if (!textToSend || isTyping || isLoading) return;

    const question = textToSend;
    const sessionId = `session-${Date.now()}`; // Tạo sessionId mới cho mỗi request
    setCurrentSessionId(sessionId);
    
    const newMessage: Message = { 
      id: `user-${Date.now()}`,
      role: 'user', 
      content: question,
      timestamp: new Date(),
      sessionId: sessionId,
      agentType: selectedAgent // Lưu agentType cho message
    };
    
    setCurrentConversation(prev => ({
      ...prev,
      messages: [...prev.messages, newMessage]
    }));
    
    // Only clear input if not using custom text
    if (!customText) {
      setInputValue('');
    }
    
    setIsTyping(true);
    setIsLoading(true);

    // Force scroll after adding user message
    setTimeout(() => {
      scrollToBottom('smooth');
    }, 50);

    // Create streaming message ID
    const streamingMessageId = `bot-${Date.now()}`;
    setCurrentStreamingMessageId(streamingMessageId);

    // Add typing indicator với sessionId
    const typingMessage: Message = { 
      id: streamingMessageId,
      role: 'bot', 
      content: 'Đang nhập...',
      timestamp: new Date(),
      sessionId: sessionId,
      isStreaming: true,
      agentType: selectedAgent // Lưu agentType cho message
    };
    setCurrentConversation(prev => ({
      ...prev,
      messages: [...prev.messages, typingMessage]
    }));

    // Choose API based on mode
    const apiUrl = getApiUrl(selectedAgent);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);
      
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ content: question }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Lỗi phản hồi từ máy chủ (${response.status}): ${errorText}`);
      }

      // Handle streaming responses
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('text/stream') || contentType.includes('application/x-ndjson')) {
        await handleStreamingResponse(response, streamingMessageId, sessionId);
      } else {
        // Handle regular JSON response
        const data = await response.json();
        let reply = "Không có phản hồi.";
        if (data.content) {
          reply = data.content;
        } else if (data.message) {
          reply = data.message;
        } else if (data.response) {
          reply = data.response;
        } else if (typeof data === 'string') {
          reply = data;
        }
        
        // Update the existing streaming message
        setCurrentConversation(prev => ({
          ...prev,
          messages: prev.messages.map(msg => 
            msg.id === streamingMessageId 
              ? { ...msg, content: reply, isStreaming: false }
              : msg
          )
        }));
      }

    } catch (error) {
      console.error("Lỗi gửi tin nhắn:", error);
      
      let errorContent = "Đã xảy ra lỗi khi gửi tin nhắn.";
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          errorContent = "Yêu cầu bị timeout. Vui lòng thử lại sau.";
        } else if (error.message.includes('Failed to fetch')) {
          errorContent = "Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng hoặc thử lại sau.";
        } else {
          errorContent = `Lỗi: ${error.message}`;
        }
      }
      
      // Remove typing indicator and add error message
      const errorMessage: Message = { 
        id: `error-${Date.now()}`,
        role: 'bot', 
        content: errorContent,
        timestamp: new Date(),
        sessionId: sessionId,
        agentType: selectedAgent
      };
      setCurrentConversation(prev => ({
        ...prev,
        messages: [...prev.messages.filter(msg => msg.content !== 'Đang nhập...'), errorMessage]
      }));
    } finally {
      setIsTyping(false);
      setIsLoading(false);
      setCurrentStreamingMessageId(null);
      setCurrentSessionId(null);
    }
  };

  const createNewConversation = () => {
    if (currentConversation.messages.length > 0) {
      const isAlreadyInHistory = chatHistory.some(conv => conv.id === currentConversation.id);
      
      if (!isAlreadyInHistory) {
        const newHistory = [{
          id: currentConversation.id,
          title: currentConversation.messages[0]?.content || "Cuộc trò chuyện mới",
          messages: currentConversation.messages
        }, ...chatHistory].slice(0, 20);
        
        setChatHistory(newHistory);
        try {
          localStorage.setItem("chatHistory", JSON.stringify(newHistory));
        } catch (error) {
          console.error("Error saving chat history:", error);
        }
      }
    }

    setCurrentConversation({
      id: generateConversationId(),
      title: "Cuộc trò chuyện mới",
      messages: []
    });

    if (window.innerWidth <= 768) {
      closeSidebar();
    }
  };

  const loadConversation = (conversation: Conversation) => {
    setCurrentConversation(conversation);
    
    if (window.innerWidth <= 768) {
      closeSidebar();
    }
  };

  const deleteConversation = (conversationId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    
    if (window.confirm('Bạn có chắc chắn muốn xóa cuộc trò chuyện này?')) {
      const updatedHistory = chatHistory.filter(conv => conv.id !== conversationId);
      setChatHistory(updatedHistory);
      
      try {
        localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));
      } catch (error) {
        console.error("Error updating chat history:", error);
      }
      
      if (currentConversation.id === conversationId) {
        setCurrentConversation({
          id: generateConversationId(),
          title: "Cuộc trò chuyện mới",
          messages: []
        });
      }
    }
  };

  const clearAllHistory = () => {
    if (window.confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện?')) {
      setChatHistory([]);
      try {
        localStorage.removeItem("chatHistory");
      } catch (error) {
        console.error("Error clearing chat history:", error);
      }
      
      setCurrentConversation({
        id: generateConversationId(),
        title: "Cuộc trò chuyện mới",
        messages: []
      });
    }
  };

  const handleStreamingResponse = async (response: Response, messageId: string, sessionId: string) => {
    if (!response.body) {
      console.error('Response body is null');
      return;
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let accumulatedContent = '';
    let isFirstChunk = true;
    let lastUpdateTime = Date.now();
    
    // Mobile-optimized update threshold
    const isMobile = window.innerWidth <= 768;
    const updateThreshold = isMobile ? 150 : 100; // Longer threshold for mobile to reduce UI updates
    
    try {
      // Process the stream
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          // Finalize the decoding when the stream is complete
          const finalChunk = decoder.decode(undefined, { stream: false });
          if (finalChunk) {
            accumulatedContent += finalChunk;
            updateMessageContent(messageId, accumulatedContent, sessionId, false);
          }
          break;
        }
        
        // Decode the current chunk
        const chunk = decoder.decode(value, { stream: true });
        accumulatedContent += chunk;
        
        // Throttle UI updates để tránh spam và cải thiện performance
        const now = Date.now();
        if (now - lastUpdateTime > updateThreshold || isFirstChunk) {
          updateMessageContent(messageId, accumulatedContent, sessionId, true);
          lastUpdateTime = now;
          isFirstChunk = false;
        }
        
        // Smaller delay for mobile to prevent UI blocking
        if (isFirstChunk) {
          await new Promise(resolve => setTimeout(resolve, isMobile ? 0 : 10));
        }
      }
    } catch (error) {
      console.error('Error reading streaming response:', error);
      updateMessageContent(
        messageId, 
        `${accumulatedContent}\n\n[Lỗi khi nhận phản hồi: ${error instanceof Error ? error.message : String(error)}]`,
        sessionId,
        false
      );
    } finally {
      // Make sure to close the reader
      reader.releaseLock();
    }
  };
  
  // Hàm để merge content từ các response fragment
  const mergeResponseContent = (existingContent: string, newContent: string): string => {
    // Nếu content mới chứa structured data (JSON), thay thế hoàn toàn
    if (newContent.includes('"tools":') || newContent.includes('"content":')) {
      return newContent;
    }
    
    // Nếu content mới chứa product data từ vector DB, thay thế hoàn toàn
    if (newContent.includes('tools:') && newContent.includes('Document(')) {
      return newContent;
    }
    
    // Nếu content hiện tại đã có structured data, không merge
    if (existingContent.includes('"tools":') || existingContent.includes('tools:')) {
      return newContent;
    }
    
    // Merge text content
    if (existingContent && existingContent !== 'Đang nhập...') {
      // Kiểm tra xem có phải là continuation của content hiện tại không
      if (newContent.startsWith(existingContent)) {
        return newContent;
      } else if (existingContent.endsWith(newContent.substring(0, Math.min(50, newContent.length)))) {
        // Tránh duplicate content
        return existingContent + newContent.substring(Math.min(50, newContent.length));
      } else {
        // Thêm content mới vào cuối
        return existingContent + '\n\n' + newContent;
      }
    }
    
    return newContent;
  };

  // Helper function to update message content với sessionId
  const updateMessageContent = (messageId: string, content: string, sessionId: string, isStreaming: boolean = false) => {
    setCurrentConversation(prev => {
      // Tìm message hiện tại
      const currentMessageIndex = prev.messages.findIndex(msg => msg.id === messageId);
      
      if (currentMessageIndex === -1) {
        // Nếu không tìm thấy message, tạo mới
        const newMessage: Message = {
          id: messageId,
          role: 'bot',
          content: content,
          timestamp: new Date(),
          sessionId: sessionId,
          isStreaming: isStreaming,
          agentType: selectedAgent
        };
        return {
          ...prev,
          messages: [...prev.messages, newMessage]
        };
      }
      
      // Merge content với content hiện tại
      const existingContent = prev.messages[currentMessageIndex].content;
      const mergedContent = mergeResponseContent(existingContent, content);
      
      // Cập nhật message hiện tại
      const updatedMessages = [...prev.messages];
      updatedMessages[currentMessageIndex] = {
        ...updatedMessages[currentMessageIndex],
        content: mergedContent,
        isStreaming: isStreaming
      };
      
      return {
        ...prev,
        messages: updatedMessages
      };
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Mobile-optimized input handling
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  // Mobile-optimized send message with touch feedback
  const handleSendMessage = () => {
    if (!inputValue.trim() || isTyping || isLoading) return;
    
    // Add touch feedback for mobile
    const sendButton = document.querySelector('.send-btn') as HTMLElement;
    if (sendButton) {
      sendButton.style.transform = 'scale(0.95)';
      setTimeout(() => {
        sendButton.style.transform = 'scale(1)';
      }, 100);
    }
    
    sendMessage();
  };

  // Mobile-optimized clear input
  const clearInput = () => {
    setInputValue('');
    
    // Add touch feedback for mobile
    const clearButton = document.querySelector('.clear-btn') as HTMLElement;
    if (clearButton) {
      clearButton.style.transform = 'scale(0.95)';
      setTimeout(() => {
        clearButton.style.transform = 'scale(1)';
      }, 100);
    }
  };

  // Function to get API URL based on selected agent
  const getApiUrl = (agentType: AgentType): string => {
    switch (agentType) {
      case 'supervisor':
        return import.meta.env.VITE_AGENT_SUPERVISOR_URL || 'http://localhost:8000/api/chat/supervisor';
      case 'vectordb':
        return import.meta.env.VITE_AGENT_VECTORDB_URL || 'http://localhost:8000/api/chat/vectordb';
      case 'deep_research':
        return import.meta.env.VITE_AGENT_DEEP_RESEARCH_URL || 'http://localhost:8000/api/chat/deep-research';
      case 'agent1':
        return import.meta.env.VITE_AGENT_1_URL || 'http://localhost:8000/api/chat/agent1';
      case 'agent2':
        return import.meta.env.VITE_AGENT_2_URL || 'http://localhost:8000/api/chat/agent2';
      default:
        return import.meta.env.VITE_AGENT_SUPERVISOR_URL || 'http://localhost:8000/api/chat/supervisor';
    }
  };

  // Function to get agent display name
  const getAgentDisplayName = (agentType: AgentType): string => {
    switch (agentType) {
      case 'supervisor':
        return 'Supervisor Agent';
      case 'vectordb':
        return 'Mega Agent';
      case 'deep_research':
        return 'Research Agent';
      case 'agent1':
        return 'Agent 1';
      case 'agent2':
        return 'Agent 2';
      default:
        return 'Supervisor Agent';
    }
  };

  const isTypingMessage = (message: Message) => {
    return message.content === 'Đang nhập...';
  };

  // Hàm để nhóm các message liên tiếp từ cùng một session
  const groupMessagesBySession = (messages: Message[]) => {
    const groupedMessages: Array<{
      sessionId: string;
      messages: Message[];
      isBotGroup: boolean;
    }> = [];
    
    let currentGroup: {
      sessionId: string;
      messages: Message[];
      isBotGroup: boolean;
    } | null = null;
    
    messages.forEach(message => {
      if (message.role === 'user') {
        // User message luôn tạo group mới
        if (currentGroup) {
          groupedMessages.push(currentGroup);
        }
        currentGroup = {
          sessionId: message.sessionId || `user-${message.id}`,
          messages: [message],
          isBotGroup: false
        };
      } else if (message.role === 'bot') {
        // Bot message có thể được nhóm với message trước đó nếu cùng session
        if (currentGroup && 
            currentGroup.isBotGroup && 
            currentGroup.sessionId === message.sessionId &&
            !isTypingMessage(message)) {
          // Thêm vào group hiện tại
          currentGroup.messages.push(message);
        } else {
          // Tạo group mới
          if (currentGroup) {
            groupedMessages.push(currentGroup);
          }
          currentGroup = {
            sessionId: message.sessionId || `bot-${message.id}`,
            messages: [message],
            isBotGroup: true
          };
        }
      }
    });
    
    // Thêm group cuối cùng
    if (currentGroup) {
      groupedMessages.push(currentGroup);
    }
    
    return groupedMessages;
  };

  // Enhanced message formatting with product cards and smooth scrolling
  const formatMessage = (content: string) => {
    // Handle empty or null content
    if (!content || content.trim() === '') {
      return '<div class="text-content">Không có nội dung</div>';
    }

    // Check if content contains structured product data from vector DB
    if (content.includes('tools:') && content.includes('Document(')) {
      return formatVectorDbResponse(content);
    }

    // Check if content contains Research Agent format
    if (content.includes('agent:') && content.includes('tools:')) {
      return formatResearchAgentResponse(content);
    }

    // Try to parse as JSON for other structured data
    let parsedData = null;
    try {
      if (content.includes('"tools":') || content.includes('"content":')) {
        const jsonMatch = content.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          parsedData = JSON.parse(jsonMatch[0]);
        }
      }
    } catch (e) {
      // Not JSON, continue with regular formatting
    }

    // If we have structured product data, format it specially
    if (parsedData && parsedData.content) {
      return formatProductMessage(parsedData.content);
    }

    // Extract Markdown images: ![alt text](url)
    const markdownImageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
    const markdownImages: Array<{ alt: string; url: string }> = [];
    
    // Find all Markdown images and extract their alt text and URLs
    let match;
    while ((match = markdownImageRegex.exec(content)) !== null) {
      const [, altText, imageUrl] = match;
      markdownImages.push({
        alt: altText || 'Product Image',
        url: imageUrl
      });
    }
    
    // Also extract direct image URLs for backward compatibility
    const directImageRegex = /(https?:\/\/\S+\.(jpg|jpeg|png|gif|bmp|webp))/gi;
    const directImages = [...content.matchAll(directImageRegex)].map(m => m[0]);
    
    // Remove all image references from text
    let textOnly = content
      .replace(markdownImageRegex, '') // Remove Markdown images
      .replace(directImageRegex, '') // Remove direct URLs
      .replace(/\[\]\([^)]+\)/g, '') // Remove empty link syntax
      .trim();
    
    // If no text content after removing images, show a placeholder
    if (!textOnly) {
      textOnly = 'Nội dung hình ảnh';
    }
    
    // Process links and formatting
    textOnly = textOnly.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="message-link">$1</a>');
    textOnly = textOnly.replace(/(<br>\s*){3,}/g, '<br><br>');
    textOnly = textOnly.replace(/\n/g, '<br>');
    
    // Enhanced text formatting for better readability
    textOnly = textOnly.replace(/(\d+\.\s*)/g, '<span class="list-number">$1</span>');
    textOnly = textOnly.replace(/(\*\*([^*]+)\*\*)/g, '<strong>$2</strong>');
    textOnly = textOnly.replace(/(\*([^*]+)\*)/g, '<em>$2</em>');
    
    let formattedContent = `<div class="text-content">${textOnly}</div>`;
    
    // Render Markdown images first (they have better context)
    if (markdownImages.length > 0) {
      formattedContent += `<div class="message-images markdown-images">`;
      markdownImages.forEach((image, index) => {
        formattedContent += `
          <div class="image-container markdown-image" data-index="${index}" style="--index: ${index}">
            <a href="${image.url}" target="_blank" title="${image.alt}" class="image-link">
              <img src="${image.url}" alt="${image.alt}" loading="lazy" 
                   onError="this.style.display='none'; this.parentElement.parentElement.classList.add('image-error');" 
                   onLoad="this.parentElement.parentElement.classList.add('image-loaded');" />
            </a>
            <div class="image-caption">${image.alt}</div>
          </div>
        `;
      });
      formattedContent += `</div>`;
    }
    
    // Render direct images if any
    if (directImages.length > 0) {
      formattedContent += `<div class="message-images direct-images">`;
      directImages.forEach((url, index) => {
        formattedContent += `
          <div class="image-container direct-image" data-index="${index}" style="--index: ${index}">
            <a href="${url}" target="_blank" class="image-link">
              <img src="${url}" alt="Product Image" loading="lazy" 
                   onError="this.style.display='none'; this.parentElement.parentElement.classList.add('image-error');" 
                   onLoad="this.parentElement.parentElement.classList.add('image-loaded');" />
            </a>
          </div>
        `;
      });
      formattedContent += `</div>`;
    }
    
    return formattedContent;
  };

  // Format vector database response with Document metadata
  const formatVectorDbResponse = (content: string) => {
    // Extract agent response and tools data
    const agentMatch = content.match(/agent:\s*([\s\S]*?)(?=tools:|$)/);
    const toolsMatch = content.match(/tools:\s*\[([\s\S]*?)\]/);
    
    let agentText = '';
    let products: Array<{
      name: string;
      price: string;
      priceUnit: string;
      url: string;
      imageUrl: string;
      category: string;
    }> = [];

    // Parse agent response
    if (agentMatch) {
      agentText = agentMatch[1].trim();
    }

    // Parse tools/documents data with improved regex
    if (toolsMatch) {
      const documentsText = toolsMatch[1];
      // More flexible Document pattern to handle multiline content
      const documentPattern = /Document\([^)]*page_content='([\s\S]*?)(?='\)|$)/g;
      let docMatch;
      
      while ((docMatch = documentPattern.exec(documentsText)) !== null) {
        let pageContent = docMatch[1];
        
        // Clean up the page content - remove trailing quotes and metadata
        pageContent = pageContent.replace(/'\),?\s*Document\(.*$/, '').trim();
        
        // Parse product data from page_content
        const productData = parseProductData(pageContent);
        if (productData) {
          products.push(productData);
        }
      }
    }

    // Create formatted response
    let formattedContent = '';
    
    // Add agent intro text if available
    if (agentText) {
      const cleanAgentText = agentText.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
      formattedContent += `<div class="text-content"><div class="product-intro">${cleanAgentText}</div></div>`;
    }
    
    // Add product grid if we have products
    if (products.length > 0) {
      formattedContent += `<div class="product-grid">`;
      
      products.forEach((product, idx) => {
        formattedContent += `
          <div class="product-card" data-index="${idx}" style="--index: ${idx}">
            <div class="product-header">
              <span class="product-index">${idx + 1}</span>
              <h3 class="product-name">${product.name}</h3>
            </div>
            <div class="product-category">${product.category}</div>
            <div class="product-image-wrapper">
              <img src="${product.imageUrl}" alt="${product.name}" loading="lazy" 
                   class="product-image"
                 onError="this.style.display='none'; this.parentElement.classList.add('image-error');" 
                 onLoad="this.parentElement.classList.add('image-loaded');" />
              <div class="product-image-overlay">
                <i class="fas fa-search-plus"></i>
              </div>
            </div>
            <div class="product-details">
              <div class="product-price">
                ${product.price}${product.priceUnit ? ' ' + product.priceUnit : ''}
              </div>
              <a href="${product.url}" target="_blank" class="product-link" ${product.url === '#' ? 'style="pointer-events: none; opacity: 0.5;"' : ''}>
                <i class="fas fa-external-link-alt"></i>
                ${product.url === '#' ? 'Không có link' : 'Xem sản phẩm'}
              </a>
            </div>
          </div>
        `;
      });
      
      formattedContent += `</div>`;
    }
    
    return formattedContent || formatRegularMessage(content);
  };

  // Parse individual product data from page_content
  const parseProductData = (pageContent: string) => {
    try {
      // Handle different line break formats
      const lines = pageContent.split(/\\n|\n/).filter(line => line.trim());
      const productData: any = {};
      
      // console.log('Parsing product data:', pageContent); // Debug log
      
      lines.forEach(line => {
        // Handle Unicode BOM and trim
        const cleanLine = line.replace(/^\ufeff/, '').trim();
        if (!cleanLine) return;
        
        const colonIndex = cleanLine.indexOf(': ');
        if (colonIndex === -1) return;
        
        const key = cleanLine.substring(0, colonIndex).trim();
        const value = cleanLine.substring(colonIndex + 2).trim();
        
        switch(key) {
          case 'product_name':
            productData.name = value;
            break;
          case 'product_price':
            // Handle various price formats and Unicode characters
            productData.price = value.replace(/\\xa0|\u00a0/g, ' ').replace(/\s+/g, ' ');
            break;
          case 'product_price_unit':
            productData.priceUnit = value;
            break;
          case 'product_url':
            productData.url = value;
            break;
          case 'image_url':
            // Fix incomplete image URLs
            if (value.startsWith('?')) {
              productData.imageUrl = 'https://mmpro.vn/media/catalog/product/cache/40feddc31972b1017c1d2c6031703b61/default.webp' + value;
            } else if (value.startsWith('http')) {
              productData.imageUrl = value;
            } else {
              // Fallback for relative URLs
              productData.imageUrl = 'https://mmpro.vn' + value;
            }
            break;
          case 'product_category':
            productData.category = value;
            break;
        }
      });
      
      // console.log('Parsed product data:', productData); // Debug log
      
      // Return data even if some fields are missing
      if (productData.name) {
        return {
          name: productData.name || 'Sản phẩm',
          price: productData.price || 'Liên hệ',
          priceUnit: productData.priceUnit || '',
          url: productData.url || '#',
          imageUrl: productData.imageUrl || '/placeholder.svg',
          category: productData.category || 'Sản phẩm'
        };
      }
      
      return null;
    } catch (error) {
      console.error('Error parsing product data:', error, pageContent);
      return null;
    }
  };

  // Format product message from structured data (legacy support)
  const formatProductMessage = (content: string) => {
    // Extract product information using regex patterns
    const productPattern = /\d+\. (.+?) - Giá: ([\d,]+\s*₫\/\w+)\s*- Link sản phẩm: \[(.+?)\]\((.+?)\)\s*- Hình ảnh: !\[(.+?)\]\((.+?)\)/g;
    const products: Array<{
      index: number;
      name: string;
      price: string;
      linkText: string;
      linkUrl: string;
      imageAlt: string;
      imageUrl: string;
    }> = [];
    
    let match;
    let index = 1;
    while ((match = productPattern.exec(content)) !== null) {
      const [, name, price, linkText, linkUrl, imageAlt, imageUrl] = match;
      products.push({
        index,
        name: name.trim(),
        price: price.trim(),
        linkText: linkText.trim(),
        linkUrl: linkUrl.trim(),
        imageAlt: imageAlt.trim(),
        imageUrl: imageUrl.trim()
      });
      index++;
    }

    if (products.length === 0) {
      return formatRegularMessage(content);
    }

    // Create beautiful product cards
    let formattedContent = `<div class="text-content">`;
    
    // Add intro text
    const introMatch = content.match(/^([^\d]+?)(?=\d+\.)/s);
    if (introMatch) {
      const introText = introMatch[1].trim().replace(/\n/g, '<br>');
      formattedContent += `<div class="product-intro">${introText}</div>`;
    }
    
    formattedContent += `</div>`;
    
    // Add product grid
    formattedContent += `<div class="product-grid">`;
    
    products.forEach((product, idx) => {
      formattedContent += `
        <div class="product-card" data-index="${idx}" style="--index: ${idx}">
          <div class="product-header">
            <span class="product-index">${product.index}</span>
            <h3 class="product-name">${product.name}</h3>
          </div>
          <div class="product-image-wrapper">
            <img src="${product.imageUrl}" alt="${product.imageAlt}" loading="lazy" 
                 class="product-image"
                 onError="this.style.display='none'; this.parentElement.classList.add('image-error');" 
                 onLoad="this.parentElement.classList.add('image-loaded');" />
            <div class="product-image-overlay">
              <i class="fas fa-search-plus"></i>
            </div>
          </div>
          <div class="product-details">
            <div class="product-price">${product.price}</div>
            <a href="${product.linkUrl}" target="_blank" class="product-link">
              <i class="fas fa-external-link-alt"></i>
              ${product.linkText}
            </a>
          </div>
        </div>
      `;
    });
    
    formattedContent += `</div>`;
    
    // Add outro text if any
    const outroMatch = content.match(/(?:Nếu anh|Nếu bạn|Anh có thể)[\s\S]*$/i);
    if (outroMatch) {
      const outroText = outroMatch[0].trim().replace(/\n/g, '<br>');
      formattedContent += `<div class="text-content"><div class="product-outro">${outroText}</div></div>`;
    }
    
    return formattedContent;
  };

  // Regular message formatting for non-product content
  const formatRegularMessage = (content: string) => {
    let textOnly = content
      .replace(/\n/g, '<br>')
      .replace(/(<br>\s*){3,}/g, '<br><br>');
    
    // Process links and formatting
    textOnly = textOnly.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="message-link">$1</a>');
    textOnly = textOnly.replace(/(\d+\.\s*)/g, '<span class="list-number">$1</span>');
    textOnly = textOnly.replace(/(\*\*([^*]+)\*\*)/g, '<strong>$2</strong>');
    textOnly = textOnly.replace(/(\*([^*]+)\*)/g, '<em>$2</em>');
    
    return `<div class="text-content">${textOnly}</div>`;
  };

  // Format Research Agent response with agent and tools sections
  const formatResearchAgentResponse = (content: string) => {
    // Handle different Research Agent response formats
    let agentText = '';
    let toolsText = '';
    
    // Try different patterns for agent and tools extraction
    const patterns = [
      // Pattern 1: agent: ... tools: ...
      {
        agent: /agent:\s*([\s\S]*?)(?=tools:|$)/i,
        tools: /tools:\s*([\s\S]*?)(?=agent:|$)/i
      },
      // Pattern 2: tools: ... agent: ...
      {
        tools: /tools:\s*([\s\S]*?)(?=agent:|$)/i,
        agent: /agent:\s*([\s\S]*?)(?=tools:|$)/i
      },
      // Pattern 3: Just agent: ...
      {
        agent: /agent:\s*([\s\S]*)/i
      },
      // Pattern 4: Just tools: ...
      {
        tools: /tools:\s*([\s\S]*)/i
      }
    ];
    
    // Try each pattern until we find matches
    for (const pattern of patterns) {
      if (pattern.agent) {
        const agentMatch = content.match(pattern.agent);
        if (agentMatch && !agentText) {
          agentText = agentMatch[1].trim();
        }
      }
      
      if (pattern.tools) {
        const toolsMatch = content.match(pattern.tools);
        if (toolsMatch && !toolsText) {
          toolsText = toolsMatch[1].trim();
        }
      }
      
      // If we found both, break
      if (agentText && toolsText) break;
    }
    
    let formattedContent = '';
    
    // Format agent text if available
    if (agentText) {
      // Clean up agent text
      const cleanAgentText = agentText
        .replace(/\\n/g, '<br>')
        .replace(/\n/g, '<br>')
        .replace(/(<br>\s*){3,}/g, '<br><br>')
        .replace(/(\*\*([^*]+)\*\*)/g, '<strong>$2</strong>')
        .replace(/(\*([^*]+)\*)/g, '<em>$2</em>');
      
      formattedContent += `<div class="text-content"><div class="research-agent-response">${cleanAgentText}</div></div>`;
    }
    
    // Format tools text if available
    if (toolsText) {
      // Clean up tools text
      const cleanToolsText = toolsText
        .replace(/\\n/g, '<br>')
        .replace(/\n/g, '<br>')
        .replace(/(<br>\s*){3,}/g, '<br><br>')
        .replace(/(\d+\.\s*)/g, '<span class="list-number">$1</span>')
        .replace(/(\*\*([^*]+)\*\*)/g, '<strong>$2</strong>')
        .replace(/(\*([^*]+)\*)/g, '<em>$2</em>');
      
      formattedContent += `<div class="text-content"><div class="research-tools-info">${cleanToolsText}</div></div>`;
    }
    
    // If no structured content found, format as regular text
    if (!agentText && !toolsText) {
      const cleanContent = content
        .replace(/\\n/g, '<br>')
        .replace(/\n/g, '<br>')
        .replace(/(<br>\s*){3,}/g, '<br><br>')
        .replace(/(\d+\.\s*)/g, '<span class="list-number">$1</span>')
        .replace(/(\*\*([^*]+)\*\*)/g, '<strong>$2</strong>')
        .replace(/(\*([^*]+)\*)/g, '<em>$2</em>');
      
      formattedContent = `<div class="text-content">${cleanContent}</div>`;
    }
    
    return formattedContent;
  };

  // Function to get agent display name for message
  const getMessageAgentName = (message: Message): string => {
    // For user messages, always show "Bạn"
    if (message.role === 'user') {
      return 'Bạn';
    }
    
    // For bot messages, use the agentType stored in the message
    if (message.agentType) {
      return getAgentDisplayName(message.agentType);
    }
    
    // Fallback: For old messages without agentType, try to detect from content
    return detectAgentTypeFromContent(message.content);
  };

  // Function to detect agent type from content (for backward compatibility)
  const detectAgentTypeFromContent = (content: string): string => {
    // Handle empty or loading content
    if (!content || content === 'Đang nhập...') {
      return getAgentDisplayName(selectedAgent);
    }
    
    // Check for Vector DB format (Mega Agent)
    if (content.includes('tools:') && content.includes('Document(')) {
      return getAgentDisplayName('vectordb');
    }
    
    // Check for Research Agent format
    if (content.includes('agent:') && content.includes('tools:')) {
      return getAgentDisplayName('deep_research');
    }
    
    // Check for other structured formats that indicate Mega Agent
    if (content.includes('"tools":') || 
        content.includes('"content":') || 
        content.includes('product_grid') ||
        content.includes('product-card')) {
      return getAgentDisplayName('vectordb');
    }
    
    // Check for simple text responses (usually Research Agent)
    if (content.length > 0 && 
        !content.includes('tools:') && 
        !content.includes('Document(') && 
        !content.includes('"tools":') && 
        !content.includes('"content":')) {
      return getAgentDisplayName('deep_research');
    }
    
    // Default based on current selected agent
    return getAgentDisplayName(selectedAgent);
  };

  // Function to convert audio blob to WAV format
  const convertToWav = async (audioBlob: Blob): Promise<Blob> => {
    try {
      // Create AudioContext to process audio
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioContext = new AudioContextClass();
      const arrayBuffer = await audioBlob.arrayBuffer();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      
      // Convert to WAV format
      const wavBuffer = audioBufferToWav(audioBuffer);
      return new Blob([wavBuffer], { type: 'audio/wav' });
    } catch (error) {
      console.error('Error converting to WAV:', error);
      // Fallback: return original blob if conversion fails
      return audioBlob;
    }
  };

  // Function to convert AudioBuffer to WAV format
  const audioBufferToWav = (buffer: AudioBuffer): ArrayBuffer => {
    const length = buffer.length;
    const numberOfChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const arrayBuffer = new ArrayBuffer(44 + length * numberOfChannels * 2);
    const view = new DataView(arrayBuffer);
    
    // WAV file header
    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * numberOfChannels * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numberOfChannels * 2, true);
    view.setUint16(32, numberOfChannels * 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length * numberOfChannels * 2, true);
    
    // Convert audio data to 16-bit PCM
    let offset = 44;
    for (let i = 0; i < length; i++) {
      for (let channel = 0; channel < numberOfChannels; channel++) {
        const sample = Math.max(-1, Math.min(1, buffer.getChannelData(channel)[i]));
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
        offset += 2;
      }
    }
    
    return arrayBuffer;
  };

  // Function to send voice to backend for STT
  const sendVoiceToSTT = async (audioBlob: Blob) => {
    try {
      console.log('Starting STT process...');
      console.log('Original audio blob:', audioBlob);
      
      // Convert audio to WAV format
      const wavBlob = await convertToWav(audioBlob);
      console.log('WAV blob created:', wavBlob);
      console.log('WAV blob size:', wavBlob.size, 'bytes');
      
      // Create FormData to send binary file
      const formData = new FormData();
      formData.append('file_bytes', wavBlob, 'audio.wav');
      
      // Log FormData contents
      console.log('FormData created with file_bytes field');
      for (const [key, value] of formData.entries()) {
        console.log('FormData field:', key, 'value type:', typeof value, 'value:', value);
      }
      
      const apiUrl = import.meta.env.VITE_VOICE_STT_URL || 'https://kha-test-ai.azurewebsites.net/api/v1/agent/tts_chat';
      console.log('Sending to STT API:', apiUrl);
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData, // Send as FormData instead of JSON
      });

      console.log('STT API response status:', response.status);
      console.log('STT API response headers:', response.headers);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('STT API error response:', errorText);
        throw new Error(`STT API error (${response.status}): ${errorText}`);
      }

      const data = await response.json();
      console.log('STT API success response:', data);
      
      const transcribedText = data.text || data.content || data.message || '';
      console.log('Transcribed text:', transcribedText);
      
      return transcribedText;
    } catch (error) {
      console.error('Error in sendVoiceToSTT:', error);
      console.error('Error details:', {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
      throw error;
    }
  };

  // Function to start voice recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      const chunks: Blob[] = [];
      
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };
      
      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: 'audio/webm' });
        setAudioChunks(chunks);
        
        try {
          setIsLoading(true);
          console.log('Processing recorded audio...');
          console.log('Audio blob size:', audioBlob.size, 'bytes');
          
          const transcribedText = await sendVoiceToSTT(audioBlob);
          
          if (transcribedText.trim()) {
            console.log('Successfully transcribed:', transcribedText);
            setInputValue(transcribedText);
            // Auto-send the transcribed text
            setTimeout(() => {
              sendMessage(transcribedText);
            }, 500);
          } else {
            console.warn('Empty transcription received');
            alert('Không thể nhận diện giọng nói. Vui lòng thử lại.');
          }
        } catch (error) {
          console.error('Error processing voice:', error);
          
          let errorMessage = 'Có lỗi xảy ra khi xử lý giọng nói.';
          
          if (error instanceof Error) {
            if (error.message.includes('STT API error')) {
              errorMessage = `Lỗi STT API: ${error.message}`;
            } else if (error.message.includes('Failed to fetch')) {
              errorMessage = 'Không thể kết nối đến STT API. Vui lòng kiểm tra kết nối mạng.';
            } else {
              errorMessage = `Lỗi: ${error.message}`;
            }
          }
          
          alert(`${errorMessage}\n\nVui lòng thử lại.`);
        } finally {
          setIsLoading(false);
        }
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };
      
      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Không thể truy cập microphone. Vui lòng kiểm tra quyền truy cập.');
    }
  };

  // Function to stop voice recording
  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      setMediaRecorder(null);
    }
  };

  // Function to test STT API connectivity
  const testSTTAPI = async () => {
    try {
      console.log('Testing STT API connectivity...');
      const apiUrl = import.meta.env.VITE_VOICE_STT_URL || 'https://kha-test-ai.azurewebsites.net/api/v1/agent/tts_chat';
      
      // Test with a minimal audio blob
      const testBlob = new Blob(['test'], { type: 'audio/wav' });
      const formData = new FormData();
      formData.append('file_bytes', testBlob, 'test.wav');
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData,
      });
      
      console.log('STT API test response status:', response.status);
      return response.ok;
    } catch (error) {
      console.error('STT API connectivity test failed:', error);
      return false;
    }
  };

  // Function to handle voice button click
  const handleVoiceButtonClick = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      // Test API connectivity before starting recording
      const isAPIAvailable = await testSTTAPI();
      if (!isAPIAvailable) {
        alert('Không thể kết nối đến STT API. Vui lòng kiểm tra kết nối mạng hoặc liên hệ admin.');
        return;
      }
      
      startRecording();
    }
  };

  return (
    <div className="home-container">
      {/* Mobile Sidebar Toggle */}
      <button 
        className="sidebar-toggle"
        onClick={toggleSidebar}
        aria-label="Toggle sidebar"
      >
        <i className="fas fa-bars"></i>
      </button>

      {/* Sidebar */}
      <div 
        className={`sidebar ${isSidebarOpen ? 'open' : ''}`}
        ref={sidebarRef}
      >
        <div className="logo-icon">
          <img src="/asset/img/techno_logo.png" alt="Logo" />
        </div>

        <nav>
          <Link to="/" onClick={closeSidebar}>
            <i className="fas fa-home"></i> 
            <span>Trang chủ</span>
          </Link>
          <a href="#" onClick={createNewConversation}>
            <i className="fas fa-plus"></i> 
            <span>Tạo mới cuộc trò chuyện</span>
          </a>
          <a href="#" onClick={clearAllHistory}>
            <i className="fas fa-trash-alt"></i>
            <span>Xóa lịch sử chat</span>
          </a>
          
          <div className="history-title">Lịch sử trò chuyện</div>
          <div className="history-list">
            {chatHistory.length === 0 ? (
              <div className="history-empty">
                <i className="fas fa-comments"></i>
                <span>Chưa có cuộc trò chuyện nào</span>
              </div>
            ) : (
              chatHistory.map((conversation) => (
                <div 
                  key={conversation.id} 
                  className={`history-item ${currentConversation.id === conversation.id ? 'active' : ''}`}
                  onClick={() => loadConversation(conversation)}
                  title={conversation.title}
                >
                  <div className="history-content">
                    <i className="fas fa-comment"></i>
                    <div className="history-details">
                      <span className="history-text">
                        {conversation.title.length > 25 
                          ? conversation.title.substring(0, 25) + '...' 
                          : conversation.title
                        }
                      </span>
                      <span className="history-time">
                        {conversation.messages.length > 0 
                          ? `${conversation.messages.length} tin nhắn`
                          : 'Trống'
                        }
                      </span>
                    </div>
                  </div>
                  <button 
                    className="delete-btn" 
                    onClick={(e) => deleteConversation(conversation.id, e)}
                    title="Xóa cuộc trò chuyện"
                    aria-label="Xóa cuộc trò chuyện"
                  >
                    <i className="fas fa-trash-alt"></i>
                  </button>
                </div>
              ))
            )}
          </div>
        </nav>
        
        <div className="bottom">
          <a href="#" onClick={closeSidebar}>
            <i className="fas fa-user"></i> 
            <span>Đăng nhập</span>
          </a>
        </div>
      </div>

      {/* Main Content */}
      <div className="main">
        <div className="chat-container" ref={chatContainerRef}>
          {currentConversation.messages.length === 0 ? (
            <div className="welcome-message">
              <div className="welcome-icon">
                <i className="fas fa-robot"></i>
              </div>
              <h2>Chào mừng bạn đến với Mega AI Assistant!</h2>
              <p>Hãy hỏi bất cứ điều gì bạn muốn biết. Tôi sẽ cố gắng giúp bạn một cách tốt nhất.</p>
              <div className="welcome-tips">
                <div className="tip-item">
                  <i className="fas fa-lightbulb"></i>
                  <span>Bạn có thể hỏi về sản phẩm, giá cả, hoặc bất kỳ thông tin nào</span>
                </div>
                <div className="tip-item">
                  <i className="fas fa-crown"></i>
                  <span>Chọn agent phù hợp để có câu trả lời chính xác nhất</span>
                </div>
              </div>
            </div>
          ) : (
            groupMessagesBySession(currentConversation.messages).map((group, groupIndex) => (
              <div key={group.sessionId} className={`message-group ${group.isBotGroup ? 'bot-group' : 'user-group'}`}>
                {group.messages.map((message, messageIndex) => (
                  <div 
                    key={message.id} 
                    ref={groupIndex === groupMessagesBySession(currentConversation.messages).length - 1 && 
                         messageIndex === group.messages.length - 1 ? lastMessageRef : null}
                    className={`message ${message.role} ${isTypingMessage(message) ? 'loading' : ''} ${
                      group.isBotGroup && group.messages.length > 1 ? 'grouped-message' : ''
                    } ${message.isStreaming ? 'isStreaming' : ''}`}
                  >
                    {/* Always show header for user messages, or first message in bot group */}
                    {(message.role === 'user' || messageIndex === 0) && (
                      <div className="message-header">
                        <strong className="sender-name">
                          {getMessageAgentName(message)}
                        </strong>
                        <span className="message-time">
                          {message.timestamp.toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'})}
                        </span>
                      </div>
                    )}
                    <div 
                      className="message-content"
                      dangerouslySetInnerHTML={{ 
                        __html: formatMessage(message.content)
                      }}
                    />
                    {/* Debug info - remove in production */}
                    {process.env.NODE_ENV === 'development' && (
                      <div style={{ fontSize: '10px', color: '#999', marginTop: '4px' }}>
                        Content length: {message.content?.length || 0} | 
                        Role: {message.role} | 
                        Session: {message.sessionId?.substring(0, 8)}...
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        <div className="search-box">
          <input 
            type="text" 
            placeholder={isLoading ? "Đang xử lý..." : "Hỏi bất cứ điều gì..."} 
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={isTyping || isLoading}
            aria-label="Nhập câu hỏi"
          />
          <div className="actions">
            <div className="agent-buttons">
              <button 
                className={`agent-btn ${selectedAgent === 'supervisor' ? 'active' : ''}`}
                onClick={() => setSelectedAgent('supervisor')}
                title="Supervisor Agent - Agent mặc định"
                aria-label="Chọn Supervisor Agent"
              >
                <i className="fas fa-crown"></i>
                <span>Supervisor</span>
              </button>
              <button 
                className={`agent-btn ${selectedAgent === 'vectordb' ? 'active' : ''}`}
                onClick={() => setSelectedAgent('vectordb')}
                title="Mega Agent - Tìm kiếm sản phẩm"
                aria-label="Chọn Mega Agent"
              >
                <i className="fas fa-brain"></i>
                <span>Mega</span>
              </button>
              <button 
                className={`agent-btn ${selectedAgent === 'deep_research' ? 'active' : ''}`}
                onClick={() => setSelectedAgent('deep_research')}
                title="Research Agent - Nghiên cứu sâu"
                aria-label="Chọn Research Agent"
              >
                <i className="fas fa-search"></i>
                <span>Research</span>
              </button>
              <button 
                className={`agent-btn ${selectedAgent === 'agent1' ? 'active' : ''}`}
                onClick={() => setSelectedAgent('agent1')}
                title="Agent 1 - Tính năng mới"
                aria-label="Chọn Agent 1"
              >
                <i className="fas fa-robot"></i>
                <span>Agent 1</span>
              </button>
            </div>
            <button 
              className="clear-btn"
              onClick={clearInput}
              disabled={!inputValue.trim()}
              title="Xóa nội dung"
              aria-label="Xóa nội dung"
            >
              <i className="fas fa-times"></i>
            </button>
            <button 
              className={`voice-btn ${isRecording ? 'recording' : ''}`}
              onClick={handleVoiceButtonClick}
              disabled={isLoading}
              title={isRecording ? "Dừng ghi âm" : "Bắt đầu ghi âm"}
              aria-label={isRecording ? "Dừng ghi âm" : "Bắt đầu ghi âm"}
            >
              <i className={`fas ${isRecording ? 'fa-stop' : 'fa-microphone'}`}></i>
            </button>
            <button 
              className="send-btn" 
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isTyping || isLoading}
              title={isLoading ? "Đang gửi..." : "Gửi tin nhắn"}
              aria-label={isLoading ? "Đang gửi..." : "Gửi tin nhắn"}
            >
              {isLoading ? (
                <i className="fas fa-spinner fa-spin"></i>
              ) : (
                <i className="fa fa-paper-plane"></i>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home; 