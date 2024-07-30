import pygame

def play_audio(file_path):
    # Initialize the mixer module
    pygame.mixer.init()
    
    # Load the audio file
    pygame.mixer.music.load(file_path)
    
    # Play the audio file
    pygame.mixer.music.play()
    
    # Wait for the music to finish playing
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

if __name__ == "__main__":
    audio_file = 'output_2024-06-21_15-04-04.mp3'  # Replace with your audio file path
    play_audio(audio_file)
