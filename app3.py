from flask import Flask, request, jsonify
import boto3
import cv2
import tempfile
import os
import io
from PIL import Image
import time
from datetime import datetime
import google.generativeai as genai
import pygame
from botocore.exceptions import ClientError
import speech_recognition as sr
import requests
import pyttsx3 as tts

app = Flask(__name__)

# Initialize AWS clients
s3_client = boto3.client("s3", region_name="ap-south-1")
rek_client = boto3.client("rekognition", region_name="ap-south-1")
db_client = boto3.client("dynamodb", region_name="ap-south-1")
polly_client = boto3.client('polly',
							aws_access_key_id="AKIA6ODU6OW7VEIYKA5D",
							aws_secret_access_key="IAT2aURrjkW59zaFd1ZXhZKE907WXyer966uM4DM",
							region_name='ap-south-1')


er1="Sorry, I didn't catch that properly"
er2="Can't process your request, please check your internet connection"

def com(command):
	cmLst=['shoot','take']
	for cm in cmLst:
		if cm in command:
			return True
	return False

def up(command):
	upLst=['upload','face','person']
	for upld in upLst:
		if upld in command:
			return True
	return False

def end(command):
	etlst=['thank you','that\'s all','thats all','exit','bye']
	for et in etlst:
		if et in command:
			return True
	return False

def gem(command):
	gemlst=["gemini","google"]
	for i in gemlst:
		if i in command:
			return True
	return False

def speak(txt):
	engine=tts.init()
	engine.setProperty('voice','HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_ZIRA_11.0')
	engine.say(txt)
	engine.runAndWait()

def convert_text_to_speech(text):
	response = polly_client.synthesize_speech(
		Text=text,
		OutputFormat='mp3',
		VoiceId='Joanna'
	)
	audio_stream = response['AudioStream'].read()
	current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
	output_filename = f'output_{current_time}.mp3'
	with open(output_filename, 'wb') as file:
		file.write(audio_stream)
	return output_filename

def listen_to_voice():
	recognizer = sr.Recognizer()
	with sr.Microphone() as source:
		recognizer.adjust_for_ambient_noise(source,duration=0.5)
		audio = recognizer.listen(source)
		try:
			text = recognizer.recognize_google(audio)
			return text
		except sr.UnknownValueError:
			return "Can you please repeat the name"
		except sr.RequestError:
			return "Can you please repeat the name"

def play_audio_file(file_path):
	pygame.mixer.init()
	pygame.mixer.music.load(file_path)
	pygame.mixer.music.play()
	while pygame.mixer.music.get_busy():
		pygame.time.Clock().tick(10)

def gemini():#full code that intigrates gemini with python
	'''This function enables the user to use Gemini on their system without opening it on their browser'''
	genai.configure(api_key="AIzaSyA9aKVprRaOwT2NblF5weiVyLnUhDXQjWo")

	generation_config = {
	"temperature": 0.6,
	"top_p": 0.95,
	"top_k": 64,
	"max_output_tokens": 500,
	"response_mime_type": "text/plain",
	}
	safety_settings = [
	{
		"category": "HARM_CATEGORY_HARASSMENT",
		"threshold": "BLOCK_MEDIUM_AND_ABOVE",
	},
	{
		"category": "HARM_CATEGORY_HATE_SPEECH",
		"threshold": "BLOCK_MEDIUM_AND_ABOVE",
	},
	{
		"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
		"threshold": "BLOCK_MEDIUM_AND_ABOVE",
	},
	{
		"category": "HARM_CATEGORY_DANGEROUS_CONTENT",
		"threshold": "BLOCK_MEDIUM_AND_ABOVE",
	},
	]

	model = genai.GenerativeModel( #this is the main code for choosing our model and specifying its configurations
	model_name="gemini-1.5-flash",
	safety_settings=safety_settings,
	generation_config=generation_config,
	system_instruction="Act like a normal human being. Give reponses that only contain words and normal punctuations"
	)

	chat= model.start_chat()
	speak("Hey what's up")
	recognizer=sr.Recognizer()#recognizer function is used to listen and understand the voice of the person giving the commands
	with sr.Microphone() as source:#this directs the program to take audio input through our microphone
		while True:
			recognizer.adjust_for_ambient_noise(source,duration=0.5)#removes the noises from the background
			audio=recognizer.listen(source)

			try:	
				text=recognizer.recognize_google(audio)#this converts the audio into text
				text=text.lower()
				if end(text):
					chat.send_message(text)
					ans=chat.text
					speak(ans)
					break
				chat.send_message(text)#This is where we give our prompt
				ans=chat.last.text
				speak(ans)
				print(ans)
			except sr.UnknownValueError:
				speak(er1)
			except sr.RequestError:
				speak(er2)
		
	return ans


def gemini_description(local_path, lst):
	def upload_to_gemini(path, mime_type=None):
		file = genai.upload_file(path, mime_type=mime_type)
		return file

	def wait_for_files_active(files):
		for name in (file.name for file in files):
			file = genai.get_file(name)
			while file.state.name == "PROCESSING":
				time.sleep(10)
				file = genai.get_file(name)
			if file.state.name != "ACTIVE":
				raise Exception(f"File {file.name} failed to process")

	genai.configure(api_key="AIzaSyBdEV4LX7Wag-eAXGa54w8gOE6pvMlwJsI")
	
	generation_config = {
	  "temperature": 1,
	  "top_p": 0.95,
	  "top_k": 64,
	  "max_output_tokens": 8192,
	  "response_mime_type": "text/plain",
	}
	
	model = genai.GenerativeModel(
	  model_name="gemini-1.5-flash",
	  generation_config=generation_config,
	)
	
	files = [
	  upload_to_gemini(local_path, mime_type="video/mp4"),
	]
	
	wait_for_files_active(files)
	
	chat_session = model.start_chat(
	  history=[
			{
				"role": "user",
				"parts": [
					files[0],
				],
			},
		]
	)
	
	response = chat_session.send_message(f"Instruction: Give a detailed description of this video in the most human way possible. Important Condition: Create an immersive experience for a blind person through your description. Describe it in a way that makes the blind person feel that he/she is living in the described moment and use simple 8th standard English. Remember: Provide the response in SSML format which is compatible with Polly. Additional Reminder: If this list {lst} contains a name then use that name in the video description as the name of the person present in the video.")
	if lst:
		response = chat_session.send_message(f"Instruction: Add the names of the people given in this list {lst} to the description you provided in the previous prompt without changing it much.")
	
	audio = convert_text_to_speech(response.text)
	play_audio_file(audio)

def download_file_from_s3(bucket_name, object_key, download_path):
	try:
		s3_client.download_file(bucket_name, object_key, download_path)
		return download_path
	except Exception as e:
		print(f"Error downloading file: {e}")
		return None

def extract_frames(local_video_path, frames_output_dir):
	cap = cv2.VideoCapture(local_video_path)
	frame_count = 0
	while cap.isOpened():
		ret, frame = cap.read()
		if not ret:
			break
		frame_count += 1
		frame_path = os.path.join(frames_output_dir, f"frame_{frame_count}.jpg")
		cv2.imwrite(frame_path, frame)
	cap.release()

def index_faces(output_dir, person_id, collection_id):
	facelst = []
	for filenames in os.listdir(output_dir):
		if filenames.endswith("jpg"):
			frame_path = os.path.join(output_dir, filenames)
			image = Image.open(frame_path)
			stream = io.BytesIO()
			image.save(stream, format="JPEG")
			image_binary = stream.getvalue()
			
			try:
				response = rek_client.index_faces(
					CollectionId=collection_id,
					Image={'Bytes': image_binary},
					ExternalImageId=person_id
				)
				for faceRecords in response["FaceRecords"]:
					faceId = faceRecords['Face']['FaceId']
					facelst.append(faceId)
			except ClientError as e:
				print(f"An error occurred: {e}")

def extract_and_analyze_frames(local_video_path, frame_skip=5):
	cap = cv2.VideoCapture(local_video_path)
	frame_count = 0
	facelst = []
	faceSet = set()
	
	while cap.isOpened():
		ret, frame = cap.read()
		if not ret:
			break
		
		if frame_count % frame_skip == 0:
			is_success, buffer = cv2.imencode(".jpg", frame)
			image_binary = buffer.tobytes()

			try:
				response = rek_client.search_faces_by_image(
					CollectionId="mon_collection",
					Image={'Bytes': image_binary},
					FaceMatchThreshold=95
				)
				
				best_match = None
				highest_confidence = 0
				for match in response['FaceMatches']:
					if match['Similarity'] > highest_confidence:
						highest_confidence = match['Similarity']
						best_match = match
				
				if best_match:
					items = best_match['Face']['ExternalImageId']
					if items:
						person = items
						facelst.append(person)
						faceSet = set(facelst)
						print(faceSet)
						
			except ClientError as e:
				if e.response['Error']['Code'] == 'InvalidParameterException':
					print("No faces detected")
				else:
					print(f"An error occurred: {e}")

		frame_count += 1
	
	cap.release()
	return faceSet

@app.route('/video-capture', methods=['POST'])
def video_capture():
	speak("Starting to record a video")
	video_path = 'point.mp4'
	fourcc = cv2.VideoWriter_fourcc(*'mp4v')
	out = cv2.VideoWriter(video_path, fourcc, 25, (640, 480))
	cap = cv2.VideoCapture(2)
	if not cap.isOpened():
		return jsonify({'error': "Can't open the camera"}), 500
	start_time = time.time()
	end_time = start_time + 15
	while time.time() <= end_time:
		ret, frame = cap.read()
		if not ret:
			return jsonify({'error': "Can't capture the frame"}), 500
		cv2.imshow("Recording", frame)
		out.write(frame)
		if cv2.waitKey(1) & 0xFF == ord('q'):
			break
	cap.release()
	out.release()
	cv2.destroyAllWindows()
	speak("Video has been recorded")
	return jsonify({'video_path': video_path})

@app.route('/process-video', methods=['POST'])
def process_video():
	video_path = request.json.get('video_path')
	if not video_path:
		return jsonify({'error': 'Video path is required'}), 400

	lst = extract_and_analyze_frames(video_path)
	speak("Generating the description of the video")
	gemini_description(video_path, lst)
	
	current_time = datetime.now()
	file_name = current_time.strftime("%D_%M_%Y_%H_%M")
	save = request.json.get('save', 'N')
	if save.upper() == 'Y':
		s3_client.upload_file(video_path, "video-recordingsss", f"{file_name}.mp4")
	os.remove(video_path)
	return jsonify({'message': 'Video processed successfully', 'faces': list(lst)})

@app.route('/face-upload', methods=['POST'])
def face_upload():
	video_path = request.json.get('video_path')
	speak("Can you tell the name of the person")
	person_id = listen_to_voice()
	while("repeat" in person_id):
		person_id=listen_to_voice()
	collection_id = request.json.get('collection_id', 'mon_collection')
	
	if not video_path or not person_id:
		return jsonify({'error': 'Video path and person ID are required'}), 400

	frames_dir = tempfile.mkdtemp()
	extract_frames(video_path, frames_dir)
	index_faces(frames_dir, person_id, collection_id)
	
	# Clean up
	for filename in os.listdir(frames_dir):
		os.remove(os.path.join(frames_dir, filename))
	os.rmdir(frames_dir)

	return jsonify({'message': 'Faces uploaded successfully'})

@app.route('/listen', methods=['GET'])
def listen_to_voice():
	recognizer = sr.Recognizer()
	with sr.Microphone() as source:
		while True:
			recognizer.adjust_for_ambient_noise(source, duration=0.5)
			speak("You can speak now")
			audio = recognizer.listen(source)
			try:
				text = recognizer.recognize_google(audio)
				if com(text.lower()):
					video=requests.post("http://127.0.0.1:5000/video-capture")
					video_path=video.json().get('video_path')
					response = requests.post('http://127.0.0.1:5000/process-video', json={'video_path': video_path,'save':'Y'})
					jsonify({'command': text})
				if up(text.lower()):
					video=requests.post("http://127.0.0.1:5000/video-capture")
					video_path=video.json().get('video_path')
					response = requests.post('http://127.0.0.1:5000/face-upload', json={'video_path': video_path})
					jsonify({'command': text})
				if gem(text.lower()):
					gemini()
				if end(text.lower()):
					speak("Have a nice day")
					return jsonify({"greetings":"Thank You"})
			except sr.UnknownValueError:
				speak('Could not comprehend what you said, Can you please repeat')
			except sr.RequestError:
				speak('Pardon me some error occured in the processing, can you please repeat')

if __name__ == "__main__":
	app.run(debug=True)
