"""Synthetic, prepared examples for Careplain's no-Gemini demo mode."""

SAMPLE_TESTS = [
    {
        "test_name": "Hemoglobin",
        "value": 11.2,
        "unit": "g/dL",
        "lower_range": 12.0,
        "upper_range": 16.0,
        "flag": "Low",
    },
    {
        "test_name": "Glucose",
        "value": 105,
        "unit": "mg/dL",
        "lower_range": 70,
        "upper_range": 140,
        "flag": "None",
    },
]

# Short, prepared examples. Test names, values, units, and ranges stay as
# synthetic report data; the surrounding explanation is translated.
_LANGUAGE_COPY = {
    "English": {
        "intro": "This is a fictional sample lab report.",
        "low": "Hemoglobin is 11.2 g/dL (reference range 12.0–16.0 g/dL) and is marked Low in this sample.",
        "normal": "Glucose is 105 mg/dL (reference range 70–140 mg/dL), within the printed range.",
        "ask": "Ask a healthcare professional how these sample results apply to you.",
        "limit": "This prepared example is not a diagnosis and is not based on a real patient.",
        "support": "It can be confusing to read lab results. Here is a calm, simple example.",
        "summary": "Simple summary", "findings": "Key findings", "questions": "Questions for your doctor", "limitations": "Limitations",
    },
    "Hindi": {
        "intro": "यह एक काल्पनिक नमूना लैब रिपोर्ट है।",
        "low": "इस नमूने में Hemoglobin 11.2 g/dL (संदर्भ सीमा 12.0–16.0 g/dL) है और इसे Low चिह्नित किया गया है।",
        "normal": "Glucose 105 mg/dL (संदर्भ सीमा 70–140 mg/dL) है, जो दी गई सीमा के भीतर है।",
        "ask": "इन नमूना परिणामों के बारे में स्वास्थ्य पेशेवर से पूछें।",
        "limit": "यह तैयार उदाहरण निदान नहीं है और किसी वास्तविक व्यक्ति की रिपोर्ट पर आधारित नहीं है।",
        "support": "लैब के परिणाम समझना कठिन हो सकता है। यह एक सरल उदाहरण है।",
        "summary": "सरल सारांश", "findings": "मुख्य परिणाम", "questions": "डॉक्टर से पूछने योग्य प्रश्न", "limitations": "सीमाएँ",
    },
    "Kannada": {
        "intro": "ಇದು ಕಲ್ಪಿತ ಮಾದರಿ ಪ್ರಯೋಗಾಲಯ ವರದಿ.",
        "low": "ಈ ಮಾದರಿಯಲ್ಲಿ Hemoglobin 11.2 g/dL (ಉಲ್ಲೇಖ ಮಿತಿ 12.0–16.0 g/dL) ಎಂದು ಇದೆ ಮತ್ತು Low ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ.",
        "normal": "Glucose 105 mg/dL (ಉಲ್ಲೇಖ ಮಿತಿ 70–140 mg/dL) ಎಂದು ಇದೆ; ಇದು ನೀಡಿದ ಮಿತಿಯೊಳಗೆ ಇದೆ.",
        "ask": "ಈ ಮಾದರಿ ಫಲಿತಾಂಶಗಳ ಬಗ್ಗೆ ಆರೋಗ್ಯ ವೃತ್ತಿಪರರನ್ನು ಕೇಳಿ.",
        "limit": "ಈ ಸಿದ್ಧಪಡಿಸಿದ ಉದಾಹರಣೆ ರೋಗನಿರ್ಣಯವಲ್ಲ ಮತ್ತು ನಿಜವಾದ ರೋಗಿಯ ವರದಿಯಲ್ಲ.",
        "support": "ಪ್ರಯೋಗಾಲಯ ಫಲಿತಾಂಶಗಳನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುವುದು ಕಷ್ಟವಾಗಬಹುದು. ಇದು ಸರಳ ಉದಾಹರಣೆ.",
        "summary": "ಸರಳ ಸಾರಾಂಶ", "findings": "ಮುಖ್ಯ ಫಲಿತಾಂಶಗಳು", "questions": "ವೈದ್ಯರನ್ನು ಕೇಳಬೇಕಾದ ಪ್ರಶ್ನೆಗಳು", "limitations": "ಮಿತಿಗಳು",
    },
    "Tamil": {
        "intro": "இது கற்பனையான மாதிரி ஆய்வக அறிக்கை.",
        "low": "இந்த மாதிரியில் Hemoglobin 11.2 g/dL (குறிப்பு வரம்பு 12.0–16.0 g/dL) என உள்ளது; Low என்று குறிக்கப்பட்டுள்ளது.",
        "normal": "Glucose 105 mg/dL (குறிப்பு வரம்பு 70–140 mg/dL) என உள்ளது; இது கொடுக்கப்பட்ட வரம்புக்குள் உள்ளது.",
        "ask": "இந்த மாதிரி முடிவுகள் பற்றி சுகாதார நிபுணரிடம் கேளுங்கள்.",
        "limit": "இந்தத் தயாரிக்கப்பட்ட எடுத்துக்காட்டு நோயறிதல் அல்ல; உண்மையான நோயாளியின் அறிக்கையும் அல்ல.",
        "support": "ஆய்வக முடிவுகளைப் புரிந்துகொள்வது கடினமாக இருக்கலாம். இது எளிய எடுத்துக்காட்டு.",
        "summary": "எளிய சுருக்கம்", "findings": "முக்கிய முடிவுகள்", "questions": "மருத்துவரிடம் கேட்க வேண்டியவை", "limitations": "வரம்புகள்",
    },
    "Telugu": {
        "intro": "ఇది కల్పిత నమూనా ప్రయోగశాల నివేదిక.",
        "low": "ఈ నమూనాలో Hemoglobin 11.2 g/dL (సూచన పరిధి 12.0–16.0 g/dL)గా ఉంది; Low అని గుర్తించారు.",
        "normal": "Glucose 105 mg/dL (సూచన పరిధి 70–140 mg/dL)గా ఉంది; ఇది ఇచ్చిన పరిధిలో ఉంది.",
        "ask": "ఈ నమూనా ఫలితాల గురించి ఆరోగ్య నిపుణుడిని అడగండి.",
        "limit": "ఈ సిద్ధం చేసిన ఉదాహరణ వైద్య నిర్ధారణ కాదు, నిజమైన రోగి నివేదిక కూడా కాదు.",
        "support": "ప్రయోగశాల ఫలితాలను అర్థం చేసుకోవడం కష్టంగా ఉండవచ్చు. ఇది సరళమైన ఉదాహరణ.",
        "summary": "సులభమైన సారాంశం", "findings": "ముఖ్య ఫలితాలు", "questions": "వైద్యుడిని అడగాల్సిన ప్రశ్నలు", "limitations": "పరిమితులు",
    },
    "Malayalam": {
        "intro": "ഇത് സാങ്കൽപ്പികമായ ഒരു മാതൃകാ ലാബ് റിപ്പോർട്ടാണ്.",
        "low": "ഈ മാതൃകയിൽ Hemoglobin 11.2 g/dL (റഫറൻസ് പരിധി 12.0–16.0 g/dL) ആണ്; Low എന്ന് അടയാളപ്പെടുത്തിയിരിക്കുന്നു.",
        "normal": "Glucose 105 mg/dL (റഫറൻസ് പരിധി 70–140 mg/dL) ആണ്; നൽകിയ പരിധിക്കുള്ളിലാണ്.",
        "ask": "ഈ മാതൃകാ ഫലങ്ങളെക്കുറിച്ച് ആരോഗ്യ വിദഗ്ധനോട് ചോദിക്കുക.",
        "limit": "ഈ തയ്യാറാക്കിയ ഉദാഹരണം രോഗനിർണയമല്ല; യഥാർത്ഥ രോഗിയുടെ റിപ്പോർട്ടുമല്ല.",
        "support": "ലാബ് ഫലങ്ങൾ മനസ്സിലാക്കുന്നത് ബുദ്ധിമുട്ടാകാം. ഇതൊരു ലളിതമായ ഉദാഹരണമാണ്.",
        "summary": "ലളിതമായ സംഗ്രഹം", "findings": "പ്രധാന കണ്ടെത്തലുകൾ", "questions": "ഡോക്ടറോട് ചോദിക്കേണ്ട ചോദ്യങ്ങൾ", "limitations": "പരിമിതികൾ",
    },
    "Bengali": {
        "intro": "এটি একটি কাল্পনিক নমুনা ল্যাব রিপোর্ট।",
        "low": "এই নমুনায় Hemoglobin 11.2 g/dL (রেফারেন্স সীমা 12.0–16.0 g/dL) এবং Low হিসেবে চিহ্নিত।",
        "normal": "Glucose 105 mg/dL (রেফারেন্স সীমা 70–140 mg/dL), দেওয়া সীমার মধ্যে।",
        "ask": "এই নমুনা ফলাফল নিয়ে একজন স্বাস্থ্য পেশাদারের সঙ্গে কথা বলুন।",
        "limit": "এই প্রস্তুত উদাহরণটি রোগ নির্ণয় নয় এবং কোনো বাস্তব রোগীর রিপোর্টের ভিত্তিতে তৈরি নয়।",
        "support": "ল্যাবের ফল বোঝা কঠিন হতে পারে। এটি একটি সহজ উদাহরণ।",
        "summary": "সহজ সারাংশ", "findings": "মূল ফলাফল", "questions": "ডাক্তারের জন্য প্রশ্ন", "limitations": "সীমাবদ্ধতা",
    },
    "Marathi": {
        "intro": "हा काल्पनिक नमुना प्रयोगशाळा अहवाल आहे.",
        "low": "या नमुन्यात Hemoglobin 11.2 g/dL (संदर्भ मर्यादा 12.0–16.0 g/dL) आहे आणि Low असे चिन्हांकित आहे.",
        "normal": "Glucose 105 mg/dL (संदर्भ मर्यादा 70–140 mg/dL) आहे; तो दिलेल्या मर्यादेत आहे.",
        "ask": "या नमुना निकालांबद्दल आरोग्यतज्ज्ञांना विचारा.",
        "limit": "हे तयार केलेले उदाहरण निदान नाही आणि खऱ्या रुग्णाच्या अहवालावर आधारित नाही.",
        "support": "प्रयोगशाळेचे निकाल समजणे कठीण असू शकते. हे एक सोपे उदाहरण आहे.",
        "summary": "सोपा सारांश", "findings": "महत्त्वाचे निष्कर्ष", "questions": "डॉक्टरांना विचारायचे प्रश्न", "limitations": "मर्यादा",
    },
}


def prepared_explanation(prompt_version, language):
    """Return a prepared synthetic explanation; never makes an API request."""
    copy = _LANGUAGE_COPY.get(language, _LANGUAGE_COPY["English"])
    body = f"{copy['intro']}\n\n{copy['low']}\n{copy['normal']}\n\n{copy['ask']}"
    if prompt_version == "V1":
        return f"{copy['support']}\n\n{body}\n\n{copy['limit']}"
    if prompt_version == "V2":
        return (
            f"## {copy['summary']}\n{copy['intro']}\n\n"
            f"## {copy['findings']}\n- {copy['low']}\n- {copy['normal']}\n\n"
            f"## {copy['questions']}\n{copy['ask']}\n\n"
            f"## {copy['limitations']}\n{copy['limit']}"
        )
    if prompt_version == "V10":
        return (
            f"## {copy['summary']}\n{copy['intro']}\n\n"
            f"## {copy['findings']}\n- {copy['low']}\n- {copy['normal']}\n\n"
            f"## {copy['questions']}\n{copy['ask']}\n\n"
            f"## {copy['limitations']}\n{copy['limit']}"
        )
    return body + f"\n\n{copy['limit']}"
