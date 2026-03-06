"""
Agent Response Translations
----------------------------
Centralized translations for all agent responses across supported languages.
"""

AGENT_RESPONSES = {
    "en": {
        "awaiting_docs": "Please upload a clear photo of your rent agreement, eviction notice, or ID card so I can extract your details automatically.",
        "awaiting_user_info": "What is your current situation regarding the eviction? Please describe the details.",
        "awaiting_consent": "Filing a Police Intimation can escalate matters with your landlord. Do I have your explicit permission to draft a police complaint regarding Wrongful Restraint under BNS Section 126?",
        "ready_to_draft": "I have all the information needed. The system will now generate your legal documents — Police Complaint, Civil Injunction Petition, and KSLSA Legal Aid Application.",
        "default": "I'm here to help with your legal situation. Please tell me more about what you're experiencing.",
    },
    "hi": {
        "awaiting_docs": "कृपया अपने किराया समझौते, बेदखली नोटिस, या ID कार्ड की स्पष्ट तस्वीर अपलोड करें ताकि मैं आपके विवरण को स्वचालित रूप से निकाल सकूँ।",
        "awaiting_user_info": "बेदखली के संबंध में आपकी वर्तमान स्थिति क्या है? कृपया विवरण बताएं।",
        "awaiting_consent": "पुलिस सूचना दाखिल करने से मामला गंभीर हो सकता है। क्या मेरे पास BNS धारा 126 के तहत गलत तरीके से रोकने की पुलिस शिकायत तैयार करने की आपकी स्पष्ट अनुमति है?",
        "ready_to_draft": "मेरे पास सभी आवश्यक जानकारी है। सिस्टम अब आपके कानूनी दस्तावेज़ तैयार करेगा।",
        "default": "मैं आपकी कानूनी स्थिति के साथ आपकी मदद करने के लिए यहाँ हूँ। कृपया बताएं कि आप क्या अनुभव कर रहे हैं।",
    },
    "ta": {
        "awaiting_docs": "உங்கள் வாடை ஒப்பந்தம், வெளியேற்றல் நோட்டீஸ் அல்லது ID கார்டின் தெளிவான புகைப்படத்தை அपलोड் செய்கிறை எனது உங்கள் விவரங்களை தானாக பிரித்தெடுக்கலாம்.",
        "awaiting_user_info": "வெளியேற்றலைப் பொறுத்து உங்கள் தற்போதைய நிலை என்ன? கृपया விவரங்களை விவரிக்கவும்.",
        "awaiting_consent": "போலீஸ் புகார் தாக்கல் செய்வது விஷயத்தை தீவிரமாக்கலாம். BNS பிரிவு 126 இன் கீழ் தவறான கட்டுப்பாடு குறித்து போலீஸ் புகார் தயாரிக்க உங்கள் வெளிப்படையான அனுமதி உள்ளதா?",
        "ready_to_draft": "எனக்கு தேவையான அனைத்து தகவல்களும் உள்ளன. கணினி இப்போது உங்கள் சட்ட ஆவணங்களை உருவாக்கும்.",
        "default": "நான் உங்கள் சட்ட நிலைமையுடன் உங்களுக்கு உதவ இங்கே இருக்கிறேன். நீங்கள் என்ன அனுபவிக்கிறீர்கள் என்பது பற்றி கூறவும்.",
    },
    "bn": {
        "awaiting_docs": "আপনার ভাড়া চুক্তি, উচ্ছেদ বিজ্ঞপ্তি বা আইডি কার্ডের একটি পরিষ্কার ফটো আপলোড করুন যাতে আমি আপনার বিবরণ স্বয়ংক্রিয়ভাবে বের করতে পারি।",
        "awaiting_user_info": "উচ্ছেদের বিষয়ে আপনার বর্তমান পরিস্থিতি কী? অনুগ্রহ করে বিবরণ বলুন।",
        "awaiting_consent": "পুলিশ অভিযোগ দায়ের করা বিষয়টি আরও গুরুতর করতে পারে। BNS ধারা 126 এর অধীনে অন্যায় বাধা সম্পর্কে পুলিশ অভিযোগ তৈরি করার জন্য আপনার স্পষ্ট অনুমতি আছে?",
        "ready_to_draft": "আমার কাছে সমস্ত প্রয়োজনীয় তথ্য আছে। সিস্টেম এখন আপনার আইনি নথি তৈরি করবে।",
        "default": "আমি আপনার আইনি পরিস্থিতিতে আপনাকে সাহায্য করতে এখানে আছি। অনুগ্রহ করে বলুন আপনি কী অনুভব করছেন।",
    }
}


def get_translated_response(response_key: str, language: str = "en") -> str:
    """Get a translated response message based on workflow status and language."""
    lang_responses = AGENT_RESPONSES.get(language, AGENT_RESPONSES["en"])
    return lang_responses.get(response_key, lang_responses.get("default", "I'm here to help."))
