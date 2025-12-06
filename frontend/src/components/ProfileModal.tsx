
import { useState, useEffect } from 'react';
import { X, Sparkles, Tag, ThumbsDown, DollarSign, Palette, Briefcase } from 'lucide-react';
import { profileApi, type UserProfile } from '../services/api';

interface ProfileModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function ProfileModal({ isOpen, onClose }: ProfileModalProps) {
    const [text, setText] = useState('');
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        if (isOpen) loadProfile();
    }, [isOpen]);

    const loadProfile = async () => {
        try {
            const data = await profileApi.get();
            setProfile(data);
        } catch (e) {
            console.error(e);
        }
    };

    const handleSubmit = async () => {
        if (!text.trim()) return;
        setIsLoading(true);
        try {
            const updated = await profileApi.update(text);
            setProfile(updated);
            setText('');
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm">
                            <Sparkles className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Your Taste Profile</h2>
                            <p className="text-sm text-gray-600">Teach Nora about your style & preferences</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/50 rounded-full transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                <div className="p-6 overflow-y-auto flex-1">
                    {/* Input Section */}
                    <div className="mb-8">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Describe your vibe
                        </label>
                        <div className="relative">
                            <textarea
                                value={text}
                                onChange={(e) => setText(e.target.value)}
                                placeholder="I'm a minimalist who loves black and white aesthetics. I need durable outdoor gear for hiking but hate flashy logos. My budget is mid-range..."
                                className="w-full p-4 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-[100px] resize-none text-gray-700"
                            />
                            <button
                                onClick={handleSubmit}
                                disabled={isLoading || !text.trim()}
                                className="absolute bottom-3 right-3 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                            >
                                {isLoading ? (
                                    <>
                                        <Sparkles className="w-4 h-4 animate-spin" />
                                        Analyzing...
                                    </>
                                ) : (
                                    'Update Profile'
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Profile Display */}
                    {profile && (
                        <div className="space-y-6">
                            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Extracted Attributes</h3>

                            {/* Warning if empty */}
                            {!profile.visual_style.length && !profile.brand_affinity.length && !profile.context.length && (
                                <div className="p-4 bg-orange-50 border border-orange-100 rounded-lg text-sm text-orange-700">
                                    ⚠️ No attributes were extracted. The AI might be having connection issues. Please try again or check the backend console.
                                </div>
                            )}

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <AttributeCard
                                    icon={<Palette className="w-4 h-4 text-purple-600" />}
                                    label="Visual Style"
                                    items={profile.visual_style}
                                    color="bg-purple-50 text-purple-700 border-purple-100"
                                />
                                <AttributeCard
                                    icon={<Tag className="w-4 h-4 text-blue-600" />}
                                    label="Brand Affinity"
                                    items={profile.brand_affinity}
                                    color="bg-blue-50 text-blue-700 border-blue-100"
                                />
                                <AttributeCard
                                    icon={<ThumbsDown className="w-4 h-4 text-red-600" />}
                                    label="Dislikes"
                                    items={profile.dislikes}
                                    color="bg-red-50 text-red-700 border-red-100"
                                />
                                <AttributeCard
                                    icon={<DollarSign className="w-4 h-4 text-green-600" />}
                                    label="Price Sensitivity"
                                    items={[profile.price_sensitivity]}
                                    color="bg-green-50 text-green-700 border-green-100"
                                />
                                <AttributeCard
                                    icon={<Briefcase className="w-4 h-4 text-amber-600" />}
                                    label="Context"
                                    items={profile.context}
                                    color="bg-amber-50 text-amber-700 border-amber-100"
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function AttributeCard({ icon, label, items, color }: { icon: any, label: string, items: string[], color: string }) {
    if (!items || items.length === 0) return null;
    return (
        <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/50">
            <div className="flex items-center gap-2 mb-3">
                {icon}
                <span className="text-sm font-medium text-gray-700">{label}</span>
            </div>
            <div className="flex flex-wrap gap-2">
                {items.map((item, i) => (
                    <span
                        key={i}
                        className={`text-xs font-medium px-2.5 py-1 rounded-full border ${color}`}
                    >
                        {item}
                    </span>
                ))}
            </div>
        </div>
    );
}
