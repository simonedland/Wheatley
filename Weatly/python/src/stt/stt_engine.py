# Speech-to-Text Engine Implementation

import speech_recognition as sr

class SpeechToTextEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def recognize_speech_from_mic(self, mic):
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Could not understand audio"
        except sr.RequestError as e:
            return f"Could not request results from Google Speech Recognition service; {e}"

    def recognize_speech_from_file(self, filename):
        # Recognize speech from an audio file
        with sr.AudioFile(filename) as source:
            audio = self.recognizer.record(source)
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Could not understand audio"
        except sr.RequestError as e:
            return f"Error from recognition service: {e}"