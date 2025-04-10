import pyttsx3

class TextToSpeechEngine:
    def __init__(self):
        # Initialize pyttsx3 engine
        self.engine = pyttsx3.init()
        # Set default properties
        self.set_speed(150)
        self.set_volume(1.0)
        voices = self.engine.getProperty('voices')
        if voices:
            self.engine.setProperty('voice', voices[0].id)
    
    def speak(self, text):
        # Speak the given text
        self.engine.say(text)
        self.engine.runAndWait()
    
    def save_to_file(self, text, filename):
        # Save spoken text to an audio file
        self.engine.save_to_file(text, filename)
        self.engine.runAndWait()
    
    def set_voice(self, voice_id):
        # Set the voice for the engine
        self.engine.setProperty('voice', voice_id)
    
    def set_speed(self, speed):
        # Set the speech rate (words per minute)
        self.engine.setProperty('rate', speed)
    
    def set_volume(self, volume):
        # Set volume between 0.0 and 1.0
        self.engine.setProperty('volume', volume)

# Example usage
if __name__ == "__main__":
    tts_engine = TextToSpeechEngine()
    tts_engine.speak("Hello, world!")