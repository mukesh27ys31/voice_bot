import threading
import time
import difflib
import re
import io

from gtts import gTTS
from googletrans import Translator
import pyttsx3  # as a fallback TTS
import speech_recognition as sr
import pygame

##########################
# CONFIGURATION SECTION
##########################

LANGUAGES = {
    "english": "en",
    "hindi": "hi",
    "telugu": "te",
    "marathi": "mr",
    "gujarati": "gu"
}

AFFIRM = {
    "en": ["yes", "yeah", "yup", "ok", "okay", "i am", "sure", "correct", "alright", "ready", "go ahead", "speaking"],
    "hi": ["हाँ", "हां", "हाँ हूं", "ठीक है", "जी", "ठीक"],
    "te": ["అవును", "సరే", "ఉన్నాను", "మాట్లాడవచ్చు", "వచ్చాను", "మాట్లాడు", "సరే చెప్పండి"],
    "mr": ["हो", "ठीक आहे", "बोलू शकतो"],
    "gu": ["હા", "હા છું", "હા બોલો", "સાચું"],
}
DENY = {
    "en": ["no", "nope", "not now", "busy", "don't", "later"],
    "hi": ["नहीं", "नहि", "अभी नहीं", "व्यस्त", "नहीं चाहिए"],
    "te": ["కాదు", "వద్దు", "ఇంకాదురా", "నాకవసరం లేదు"],
    "mr": ["नाही", "वेळ नाही", "नको"],
    "gu": ["ના", "હવે નહિ", "પછી"],
}
REASONS = {
    "paid": {
        "en": ["already paid", "payment done", "paid"],
        "hi": ["पहले ही चुका दिया", "भुगतान हो गया", "भुगतान किया है"],
        "te": ["ఇప్పటికే చెల్లించాను", "పేమెంట్ అయ్యింది"],
        "mr": ["अगोदरच भरले"],
        "gu": ["પહેલાં જ ચુકવણી કરી"],
    },
    "finance": {
        "en": ["finance", "money", "job", "problem", "no cash", "no money"],
        "hi": ["पैसे नहीं", "नौकरी नहीं", "वित्तीय समस्या", "धन की कमी"],
        "te": ["ఫైనాన్స్", "డబ్బులు లేవు", "ఆర్థిక సమస్య"],
        "mr": ["पैसा नाही", "आर्थिक अडचण"],
        "gu": ["પૈસા નથી", "નાણાં નથી", "નોકરી નથી"],
    },
    "not_interested": {
        "en": ["not interested", "returns", "market", "better", "other"],
        "hi": ["रुचि नहीं", "बाजार", "रिटर्न नहीं"],
        "te": ["ఆసక్తి లేదు", "మరేం అవసరం లేదు"],
        "mr": ["मन नाही", "व्याज नाही"],
        "gu": ["મને રસ નથી"],
    }
}
##########################
# VOCAL UI
##########################

translator = Translator()
selected_language = 'en'
lang_name = 'english'
pygame.mixer.init()

def speak(text):
    try:
        translated = text
        if selected_language != 'en':
            translated = translator.translate(text, dest=selected_language).text
    except Exception as e:
        print(f"Translation failed (error: {e}). Using original text.")
        translated = text

    print(f"VEENA: {translated}")
    try:
        tts = gTTS(text=translated, lang=selected_language)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        pygame.mixer.music.load(fp, 'mp3')
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    except Exception as e:
        print("TTS fallback:", e)
        local_tts(translated)

def local_tts(text):
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("Local TTS failed:", e)

def listen():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source)
            print("VEENA: Listening...")  # Only print, do NOT say.
            audio = r.listen(source, phrase_time_limit=7)
        text = r.recognize_google(audio, language=selected_language)
        print("USER:", text)
        return text.lower()
    except Exception:
        speak("Sorry, I didn’t catch that. Please repeat.")
        return ""

def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def fuzzy_match(user_response, categories, lang=None):
    if not lang:
        lang = selected_language
    normalized = normalize(user_response)
    phrases = []
    for val in categories.values():
        phrases += val.get(lang, [])
    for p in phrases:
        if normalize(p) in normalized or normalized in normalize(p):
            return True
    matches = difflib.get_close_matches(normalized, [normalize(p) for p in phrases], n=1, cutoff=0.7)
    return bool(matches)

def fuzzy_match_category(response, options):
    norm_response = normalize(response)
    all_opts = [normalize(option) for option in options]
    for option in all_opts:
        if option in norm_response or norm_response in option:
            return option
    matches = difflib.get_close_matches(norm_response, all_opts, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return None

def select_language():
    global selected_language, lang_name
    valid_ans = list(LANGUAGES.keys())
    speak("Please say your preferred language: English, Hindi, Telugu, Marathi or Gujarati.")
    while True:
        response = listen()
        if response in valid_ans:
            selected_language = LANGUAGES[response]
            lang_name = response
            speak(f"Language set to {response.title()}.")
            break
        speak("I did not recognize that language. Please repeat or say English, Hindi, Telugu, Marathi or Gujarati.")

def prompt_until_valid(question, options_dict=None, fallback_aff=None, fallback_deny=None, max_tries=3):
    for i in range(max_tries):
        speak(question)
        response = listen()
        if not response:
            continue
        if options_dict:
            for label, opts in options_dict.items():
                match = fuzzy_match_category(response, opts.get(selected_language, opts['en']))
                if match:
                    return label, match
        if fallback_aff and fuzzy_match_category(response, fallback_aff.get(selected_language, fallback_aff['en'])):
            return "affirm", ""
        if fallback_deny and fuzzy_match_category(response, fallback_deny.get(selected_language, fallback_deny['en'])):
            return "deny", ""
    return None, ""

MOTIVATIONAL_STEPS = {
    "en": [
        "I understand life gets busy. Renewing your policy ensures your family's financial protection, whatever happens.",
        "Every premium you pay grows your savings, protects your future, and brings you tax benefits and loyalty rewards.",
        "Imagine facing a crisis with confidence—your decision today could completely change your family's tomorrow.",
        "Would a flexible installment or EMI arrangement help? Or can I answer any concerns holding you back?",
        "Remember, one thoughtful action now safeguards your loved ones' dreams for a lifetime."
    ],
    "hi": [
        "मैं समझ सकता हूँ कि ज़िन्दगी में व्यस्तता होती है। प्रीमियम भरने से आपका परिवार हर हाल में सुरक्षित रहेगा।",
        "हर प्रीमियम से आपकी बचत और टैक्स छूट बढ़ती है, और आपको विशेष रिवार्ड्स मिलते हैं।",
        "कल्पना कीजिए किसी संकट में आपके परिजन बिना चिंता के रहें—आज का फैसला उनका भविष्य बदल सकता है।",
        "क्या आपकी सुविधा के लिए हम ईएमआई या आसान भुगतान विकल्प दे सकते हैं?",
        "आज का एक निर्णय आपके परिवार की खुशियाँ बनाए रखेगा।"
    ],
    "te": [
        "మీరు బిజీగా ఉండొచ్చు. పాలసీ కొనసాగితే మీ కుటుంబం విపత్కర సమయాల్లో భాగస్వామ్యం పొందుతుంది.",
        "మీ ప్రతి పేమెంట్ మీ సొమ్మును పెంచడమే కాకుండా, పన్ను లాభాలు, లాయల్టీ బోనస్ లభిస్తాయి.",
        "ఘటనలు అనుకోకుండా జరుగుతాయి—మీ నిర్ణయం మీ కుటుంబ భవిష్యత్తును కాపాడుతుంది.",
        "మీకు EMI లేదా సులభమైన చెల్లింపు మార్గాలు కావాలా?",
        "ఇప్పుడు తీసుకున్న చిన్న నిర్ణయం జీవితాంతం మీ కుటుంబాన్ని కాపాడుతుంది."
    ],
    "mr": [
        "आरामशीरपणे समजतो की कधी कधी जीवन धावपळीचे असते. प्रीमियम भरल्यास तुमच्या कुटुंबाचे भवितव्य सुरक्षित राहते.",
        "प्रत्येक प्रीमियममुळे तुमची गुंतवणूक, कर सवलत आणि लॉयल्टी बक्षिसे वाढतात.",
        "कल्पना करा—अचानकच्या संकटामध्ये तुम्ही निर्धास्त असाल.",
        "इएमआय किंवा सोयीचे पर्याय हवे असल्यास सांगा.",
        "आजचा निर्णय तुमच्या कुटुंबाचे जीवनभर रक्षण करेल."
    ],
    "gu": [
        "મને ખબર છે કે જીવન વ્યસ્ત છે. પણ પોલિસી ચાલુ રાખવાથી તમારો પરિવાર દરેક પરિસ્થિતિમાં સુરક્ષિત રહેશે.",
        "દરેક કિસ્ત સાથે તમારો ફંડ વધે છે, ટેક્સ-છૂટ મળે છે, અને વિશેષ ફાયદા મળે છે.",
        "રેંડમ દુઃખઘટનામાં પણ તમારા પરિવારને સપોર્ટ મળશે.",
        "તમે ઇએમઆઈ અથવા મહિનો પેમેન્ટ મોડ પસંદ કરી શકો છો.",
        "આજનું નાનું પગલું જીવનભર સુરક્ષા આપે છે."
    ]
}

def motivate_strongly(lang, max_tries=5):
    steps = MOTIVATIONAL_STEPS.get(lang, MOTIVATIONAL_STEPS["en"])
    for i in range(min(max_tries, len(steps))):
        speak(steps[i])
        label, _ = prompt_until_valid(
            "Would you like to renew your policy now?",
            options_dict={"affirm": AFFIRM, "deny": DENY}
        )
        if label == "affirm":
            return True
    return False

def veena_conversation():
    speak("Hello! This is Veena, your virtual Insurance assistant. Welcome to ValuEnable Life Insurance. I’m here to assist you regarding your policy and help with any queries you may have.")
    select_language()
    policy = {
        "policy_holder": "Prathik Jadhav",
        "gender": "male",
        "policy_number": "VE123456789",
        "product": "SmartProtect",
        "policy_start_date": "10 August 2020",
        "total_premium_paid": "₹1,00,000",
        "outstanding_amount": "₹10,000",
        "premium_due_date": "30 June 2024"
    }
    pronoun = "Mr." if policy["gender"] == "male" else "Ms."

    _, answer = prompt_until_valid(
        f"May I speak with {pronoun} {policy['policy_holder']}?",
        options_dict={"affirm": AFFIRM, "deny": DENY},
        fallback_aff=AFFIRM, fallback_deny=DENY
    )
    if answer in DENY[selected_language] or answer == "":
        speak("Okay. Thank you. Have a good day.")
        return

    _, time_answer = prompt_until_valid(
        "This is a service call about your life insurance policy. May I take two minutes of your time?",
        options_dict={"affirm": AFFIRM, "deny": DENY},
        fallback_aff=AFFIRM, fallback_deny=DENY
    )
    if time_answer in DENY[selected_language] or time_answer == "":
        speak("When would be a good time to call you back?")
        listen()
        speak("Thank you. I will call you then.")
        return

    speak("Let me confirm your policy details.")
    speak(f"Your policy is ValuEnable Life {policy['product']}, number {policy['policy_number']}, started on {policy['policy_start_date']}.")
    speak(f"You have paid total premiums of {policy['total_premium_paid']}. However, {policy['outstanding_amount']} is pending since {policy['premium_due_date']}. You have no active life cover currently.")

    speak("Could you share the main reason why the premium hasn't been paid?")
    user_reason = listen()
    print("DEBUG - Freeform reason:", user_reason)

    reason_label = None
    for label, opts in {
        "paid": REASONS["paid"],
        "finance": REASONS["finance"],
        "not_interested": REASONS["not_interested"]
    }.items():
        if fuzzy_match_category(user_reason, opts.get(selected_language, opts['en'])):
            reason_label = label
            break

    deny_matched = fuzzy_match_category(user_reason, DENY.get(selected_language, DENY['en']))

    if reason_label == "paid":
        speak("Thank you for updating. May I know when and through which mode did you pay?")
        listen()
        speak("If possible, please provide the transaction or cheque number for quick reconciliation.")
        listen()
        speak("Thank you! Your record will be updated soon. Can I help you with anything else?")
        listen()
    elif reason_label == "finance":
        speak("I understand your concern. You may pay with a credit card, break into EMI, or switch to monthly mode. Would you consider any of these?")
        pay_label, pay_match = prompt_until_valid(
            "Please say yes or no.", options_dict={"affirm": AFFIRM, "deny": DENY}
        )
        print(f"DEBUG: pay_label={pay_label}, pay_match={pay_match}")
        if pay_label == "affirm":
            speak("Excellent! You can pay online or in branch, or we can send you a payment link on WhatsApp. How would you prefer to pay?")
        elif pay_label == "deny":
            if motivate_strongly(selected_language):
                speak("Great decision! You can pay online or in branch, or we can send you a payment link on WhatsApp. How would you prefer to pay?")
                prompt_until_valid(
                    "Say yes if you want the link.", options_dict={"affirm": AFFIRM, "deny": DENY}
                )
                speak("Thank you! I will send the payment link. For help, call 1800 209 7272 or WhatsApp 8806727272.")
            else:
                speak("Thank you for sharing your thoughts. Your family’s protection is always important to us. Please remember, you can pay before the due date to keep your life cover active. For any assistance, we're always here for you.")
        else:
            speak("Thank you for letting us know. If you need any help or face any issue, our team can assist you online or over phone.")
            listen()

    elif reason_label == "not_interested" or deny_matched:
        if motivate_strongly(selected_language):
            speak("Great decision! You can pay online or in branch, or we can send you a payment link on WhatsApp. How would you prefer to pay?")
            prompt_until_valid(
                "Say yes if you want the link.", options_dict={"affirm": AFFIRM, "deny": DENY}
            )
            speak("Thank you! I will send the payment link. For help, call 1800 209 7272 or WhatsApp 8806727272.")
        else:
            speak("Thank you for sharing your thoughts. Your family’s protection is always important to us. Please remember, you can pay before the due date to keep your life cover active. For any assistance, we're always here for you.")
    else:
        speak("Thank you for letting us know. If you need any help or face any issue, our team can assist you online or over phone.")
        listen()

    speak("Thank you for your time. For assistance, call 1800 209 7272 or WhatsApp 8806727272. Goodbye.")

if __name__ == '__main__':
    veena_conversation()

