import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Message } from '../types';
import { ProductCard } from './ProductCard';
import { chatApi, type ChatMessage } from '../services/api';
import { Send, Sparkles, Bot, User } from 'lucide-react';

export function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: "Hi! I'm Nora, your AI shopping assistant. I've analyzed your browsing history and I'm ready to help you find products. Try asking me about what you've been looking at, or ask for recommendations!",
            timestamp: new Date(),
        },
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [streamingContent, setStreamingContent] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, streamingContent]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);
        setStreamingContent('');

        // Convert to API format
        const history: ChatMessage[] = messages.map((m) => ({
            role: m.role,
            content: m.content,
        }));

        chatApi.streamMessage(
            input,
            history,
            (data) => {
                if (data.type === 'content') {
                    setStreamingContent((prev) => prev + data.value);
                } else if (data.type === 'done') {
                    const products = data.products?.length > 0 ? data.products : undefined;
                    console.log('Received products:', products);

                    const aiMessage: Message = {
                        id: (Date.now() + 1).toString(),
                        role: 'assistant',
                        content: data.full_response,
                        products: products,
                        timestamp: new Date(),
                    };
                    setMessages((prev) => [...prev, aiMessage]);
                    setStreamingContent('');
                    setIsLoading(false);
                } else if (data.type === 'error') {
                    console.error('Stream error:', data.message);
                    setIsLoading(false);
                }
            }
        );
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-full bg-gray-100">
            {/* Header */}
            <div className="border-b border-gray-200 px-6 py-4 bg-white shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
                        <Sparkles className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-semibold text-gray-900">Nora</h1>
                        <p className="text-sm text-gray-500">AI Shopping Assistant</p>
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
                    >
                        <div
                            className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow ${message.role === 'user' ? 'bg-blue-600' : 'bg-white border border-gray-200'
                                }`}
                        >
                            {message.role === 'user' ? (
                                <User className="w-4 h-4 text-white" />
                            ) : (
                                <Bot className="w-4 h-4 text-gray-700" />
                            )}
                        </div>
                        <div className={`flex-1 ${message.role === 'user' ? 'flex justify-end' : ''}`}>
                            <div
                                className={`inline-block max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${message.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-tr-sm'
                                    : 'bg-white text-gray-800 rounded-tl-sm border border-gray-100'
                                    }`}
                            >
                                <div className="text-sm leading-relaxed">
                                    {message.role === 'assistant' ? (
                                        <ReactMarkdown
                                            components={{
                                                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                                ul: ({ children }) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
                                                ol: ({ children }) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
                                                li: ({ children }) => <li className="mb-1">{children}</li>,
                                                strong: ({ children }) => <strong className="font-semibold text-blue-600">{children}</strong>,
                                            }}
                                        >
                                            {message.content}
                                        </ReactMarkdown>
                                    ) : (
                                        message.content
                                    )}
                                </div>
                            </div>

                            {/* Product Cards */}
                            {message.products && message.products.length > 0 && (
                                <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                                    {message.products.map((product, idx) => (
                                        <ProductCard key={product.id || idx} product={product} />
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {/* Streaming message */}
                {isLoading && (
                    <div className="flex gap-3">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-white border border-gray-200 shadow">
                            <Bot className="w-4 h-4 text-gray-700" />
                        </div>
                        <div className="flex-1">
                            <div className="inline-block max-w-[85%] bg-white text-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-100">
                                <div className="text-sm leading-relaxed">
                                    {streamingContent ? (
                                        <ReactMarkdown>{streamingContent}</ReactMarkdown>
                                    ) : (
                                        <div className="flex items-center gap-1.5">
                                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-gray-200 px-6 py-4 bg-white shadow-lg">
                <div className="flex gap-3">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyPress}
                        placeholder="Ask about your browsing history or request recommendations..."
                        className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50"
                        disabled={isLoading}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || isLoading}
                        className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-md"
                    >
                        <Send className="w-4 h-4" />
                        Send
                    </button>
                </div>
                <p className="text-xs text-gray-400 mt-2 text-center">
                    Powered by GPT-4o-mini with RAG
                </p>
            </div>
        </div>
    );
}
