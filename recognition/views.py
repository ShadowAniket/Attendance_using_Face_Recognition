from django.shortcuts import render,redirect
from .forms import usernameForm,DateForm,UsernameAndDateForm, DateForm_2
from django.contrib import messages
from django.contrib.auth.models import User
import cv2
import dlib
import imutils
from imutils import face_utils
from imutils.video import VideoStream
from imutils.face_utils import rect_to_bb
from imutils.face_utils import FaceAligner
import time
from attendance_system_facial_recognition.settings import BASE_DIR
import os
import face_recognition
from face_recognition.face_recognition_cli import image_files_in_folder
import pickle
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
import numpy as np
from django.contrib.auth.decorators import login_required
import matplotlib as mpl
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import datetime
from django_pandas.io import read_frame
from users.models import Present, Time
import seaborn as sns
import pandas as pd
from django.db.models import Count
#import mpld3
import matplotlib.pyplot as plt
from pandas.plotting import register_matplotlib_converters
from matplotlib import rcParams
import math
from scipy.spatial import distance as dist
import mediapipe as mp

#backend matplotlib mitigating interactive GUI risk
mpl.use('Agg')

#To check user exists in system by username
def username_present(username):
	if User.objects.filter(username=username).exists():
		return True	
	return False


def create_dataset(username):
	id = username
	#checks if user exist logic --
	if(os.path.exists('face_recognition_data/training_dataset/{}/'.format(id))==False):
		os.makedirs('face_recognition_data/training_dataset/{}/'.format(id))
	directory='face_recognition_data/training_dataset/{}/'.format(id)
	#initialize face detection and shape predictor --
	detector = dlib.get_frontal_face_detector()
	predictor = dlib.shape_predictor('face_recognition_data/shape_predictor_68_face_landmarks.dat')   #Add path to the shape predictor ######CHANGE TO RELATIVE PATH LATER
	fa = FaceAligner(predictor , desiredFaceWidth = 96)
	
	vs = VideoStream(src=0).start()
	#time.sleep(2.0) ####CHECK######
	sampleNum = 0
	while(True):
		frame = vs.read()
		frame = imutils.resize(frame ,width = 800)
		gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		faces = detector(gray_frame,0)
		for face in faces:
			print("inside for loop")
			(x,y,w,h) = face_utils.rect_to_bb(face)
			face_aligned = fa.align(frame,gray_frame,face)
			sampleNum = sampleNum+1
			if face is None:
				print("face is none")
				continue
			cv2.imwrite(directory+'/'+str(sampleNum)+'.jpg'	, face_aligned)
			face_aligned = imutils.resize(face_aligned ,width = 400)
			cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),1)
			cv2.waitKey(1)
		cv2.imshow("Add Images",frame)
		cv2.waitKey(1)
		if(sampleNum>300):
			break
	vs.stop()
	cv2.destroyAllWindows()

def predict(face_aligned,svc,threshold=0.7):
	face_encodings=np.zeros((1,128))
	try:
		x_face_locations=face_recognition.face_locations(face_aligned)
		faces_encodings=face_recognition.face_encodings(face_aligned,known_face_locations=x_face_locations)
		if(len(faces_encodings)==0):
			return ([-1],[0])
	except:
		return ([-1],[0])
	prob=svc.predict_proba(faces_encodings)
	result=np.where(prob[0]==np.amax(prob[0]))
	if(prob[0][result[0]]<=threshold):
		return ([-1],prob[0][result[0]])
	return (result[0],prob[0][result[0]])


def vizualize_Data(embedded, targets,):	
	X_embedded = TSNE(n_components=2).fit_transform(embedded)
	for i, t in enumerate(set(targets)):
		idx = targets == t
		plt.scatter(X_embedded[idx, 0], X_embedded[idx, 1], label=t)
	plt.legend(bbox_to_anchor=(1, 1))
	rcParams.update({'figure.autolayout': True})
	plt.tight_layout()	
	plt.savefig('./recognition/static/recognition/img/training_visualisation.png')
	plt.close()


def update_attendance_in_db_in(present):
    today = datetime.date.today()
    time = datetime.datetime.now()
    
    for person in present:
        try:
            # Try to find the user in the database
            user = User.objects.get(username=person)
        except User.DoesNotExist:
            # Handle the case where the user is not found
            print(f"User '{person}' does not exist in the database.")
            return False  # Returning False on failure to update DB

        try:
            # Check if attendance for this user on this date already exists
            qs = Present.objects.get(user=user, date=today)
        except Present.DoesNotExist:
            qs = None
            
        # If attendance record does not exist, create one
        if qs is None:
            if present[person] == True:
                a = Present(user=user, date=today, present=True)
                a.save()
            else:
                a = Present(user=user, date=today, present=False)
                a.save()
        else:
            # If attendance record exists, update the 'present' status
            if present[person] == True:
                qs.present = True
                qs.save(update_fields=['present'])

        # Log the time if the user is marked present
        if present[person] == True:
            a = Time(user=user, date=today, time=time, out=False)
            a.save()
    
    return True  #  True when successful



def update_attendance_in_db_out(present):
    today = datetime.date.today()
    time_now = datetime.datetime.now()    
    for person in present:
        if present[person] == True:
            user = User.objects.get(username=person)
            last_entry = Time.objects.filter(user=user, date=today, out=False).order_by('-time').first()            
            if last_entry:
                last_entry.out = True
                last_entry.time = time_now
                last_entry.save(update_fields=['out', 'time'])
            else:
                new_entry = Time(user=user, date=today, time=time_now, out=True)
                new_entry.save()


def check_validity_times(times_all):
    if len(times_all) == 0:
        return False, 0
    sign = times_all.first().out
    times_in = times_all.filter(out=False)
    times_out = times_all.filter(out=True)
    if len(times_in) != len(times_out):
        return False, 0
    break_hours = 0
    prev_time = times_all.first().time
    prev_out = times_all.first().out
    for obj in times_all:
        current_out = obj.out
        if current_out == prev_out:
            return False, 0        
        if current_out:
            to_time = obj.time
            break_hours += (to_time - prev_time).total_seconds() / 3600.0
        else:
            prev_time = obj.time        
        prev_out = current_out    
    return True, break_hours


def convert_hours_to_hours_mins(hours):	
	h=int(hours)
	hours-=h
	m=hours*60
	m=math.ceil(m)
	return str(str(h)+ " hrs " + str(m) + "  mins")

def hours_vs_date_given_employee(present_qs,time_qs,admin=True):
	register_matplotlib_converters()
	df_hours=[]
	df_break_hours=[]
	qs=present_qs
	for obj in qs:
		date=obj.date
		times_in=time_qs.filter(date=date).filter(out=False).order_by('time')
		times_out=time_qs.filter(date=date).filter(out=True).order_by('time')
		times_all=time_qs.filter(date=date).order_by('time')
		obj.time_in=None
		obj.time_out=None
		obj.hours=0
		obj.break_hours=0
		if (len(times_in)>0):			
			obj.time_in=times_in.first().time
		if (len(times_out)>0):
			obj.time_out=times_out.last().time
		if(obj.time_in is not None and obj.time_out is not None):
			ti=obj.time_in
			to=obj.time_out
			hours=((to-ti).total_seconds())/3600
			obj.hours=hours
		
		else:
			obj.hours=0
		(check,break_hourss)= check_validity_times(times_all)
		if check:
			obj.break_hours=break_hourss
		else:
			obj.break_hours=0
		df_hours.append(obj.hours)
		df_break_hours.append(obj.break_hours)
		obj.hours=convert_hours_to_hours_mins(obj.hours)
		obj.break_hours=convert_hours_to_hours_mins(obj.break_hours)
			
	df = read_frame(qs)	
	df["hours"]=df_hours
	df["break_hours"]=df_break_hours
	print(df)	
	sns.barplot(data=df,x='date',y='hours')
	plt.xticks(rotation='vertical')
	rcParams.update({'figure.autolayout': True})
	plt.tight_layout()
	if(admin):
		plt.savefig('./recognition/static/recognition/img/attendance_graphs/hours_vs_date/1.png')
		plt.close()
	else:
		plt.savefig('./recognition/static/recognition/img/attendance_graphs/employee_login/1.png')
		plt.close()
	return qs

def hours_vs_employee_given_date(present_qs,time_qs):
	register_matplotlib_converters()
	df_hours=[]
	df_break_hours=[]
	df_username=[]
	qs=present_qs
	for obj in qs:
		user=obj.user
		times_in=time_qs.filter(user=user).filter(out=False)
		times_out=time_qs.filter(user=user).filter(out=True)
		times_all=time_qs.filter(user=user)
		obj.time_in=None
		obj.time_out=None
		obj.hours=0
		obj.hours=0
		if (len(times_in)>0):			
			obj.time_in=times_in.first().time
		if (len(times_out)>0):
			obj.time_out=times_out.last().time
		if(obj.time_in is not None and obj.time_out is not None):
			ti=obj.time_in
			to=obj.time_out
			hours=((to-ti).total_seconds())/3600
			obj.hours=hours
		else:
			obj.hours=0
		(check,break_hourss)= check_validity_times(times_all)
		if check:
			obj.break_hours=break_hourss
		else:
			obj.break_hours=0
		df_hours.append(obj.hours)
		df_username.append(user.username)
		df_break_hours.append(obj.break_hours)
		obj.hours=convert_hours_to_hours_mins(obj.hours)
		obj.break_hours=convert_hours_to_hours_mins(obj.break_hours)
	df = read_frame(qs)	
	df['hours']=df_hours
	df['username']=df_username
	df["break_hours"]=df_break_hours
	sns.barplot(data=df,x='username',y='hours')
	plt.xticks(rotation='vertical')
	rcParams.update({'figure.autolayout': True})
	plt.tight_layout()
	plt.savefig('./recognition/static/recognition/img/attendance_graphs/hours_vs_employee/1.png')
	plt.close()
	return qs

def total_number_employees():
	qs=User.objects.all()
	return (len(qs) -1)
	# -1 to account for admin 

def employees_present_today():
	today=datetime.date.today()
	qs=Present.objects.filter(date=today).filter(present=True)
	return len(qs)

def this_week_emp_count_vs_date():
	today=datetime.date.today()
	some_day_last_week=today-datetime.timedelta(days=7)
	monday_of_last_week=some_day_last_week-  datetime.timedelta(days=(some_day_last_week.isocalendar()[2] - 1))
	monday_of_this_week = monday_of_last_week + datetime.timedelta(days=7)
	qs=Present.objects.filter(date__gte=monday_of_this_week).filter(date__lte=today)
	str_dates=[]
	emp_count=[]
	str_dates_all=[]
	emp_cnt_all=[]
	cnt=0
	for obj in qs:
		date=obj.date
		str_dates.append(str(date))
		qs=Present.objects.filter(date=date).filter(present=True)
		emp_count.append(len(qs))	
	while(cnt<5):
		date=str(monday_of_this_week+datetime.timedelta(days=cnt))
		cnt+=1
		str_dates_all.append(date)
		if(str_dates.count(date))>0:
			idx=str_dates.index(date)
			emp_cnt_all.append(emp_count[idx])
		else:
			emp_cnt_all.append(0)
	df=pd.DataFrame()
	df["Date"]=str_dates_all
	df["Number of Students"]=emp_cnt_all
	sns.lineplot(data=df,x='Date',y='Number of Students')
	plt.savefig('./recognition/static/recognition/img/attendance_graphs/this_week/1.png')
	plt.close()

def last_week_emp_count_vs_date():
	today=datetime.date.today()
	some_day_last_week=today-datetime.timedelta(days=7)
	monday_of_last_week=some_day_last_week-  datetime.timedelta(days=(some_day_last_week.isocalendar()[2] - 1))
	monday_of_this_week = monday_of_last_week + datetime.timedelta(days=7)
	qs=Present.objects.filter(date__gte=monday_of_last_week).filter(date__lt=monday_of_this_week)
	str_dates=[]
	emp_count=[]
	str_dates_all=[]
	emp_cnt_all=[]
	cnt=0
	for obj in qs:
		date=obj.date
		str_dates.append(str(date))
		qs=Present.objects.filter(date=date).filter(present=True)
		emp_count.append(len(qs))

	while(cnt<5):
		date=str(monday_of_last_week+datetime.timedelta(days=cnt))
		cnt+=1
		str_dates_all.append(date)
		if(str_dates.count(date))>0:
			idx=str_dates.index(date)
			emp_cnt_all.append(emp_count[idx])
		else:
			emp_cnt_all.append(0)
	df=pd.DataFrame()
	df["Date"]=str_dates_all
	df["Number of Students"]=emp_cnt_all
	sns.lineplot(data=df,x='Date',y='Number of Students')
	plt.savefig('./recognition/static/recognition/img/attendance_graphs/last_week/1.png')
	plt.close()


def home(request):
	return render(request, 'recognition/home.html')
def layout(request):
	return render(request, 'recognition/Layout.html')
def layout2(request):
	return render(request, 'recognition/layout2.html')

@login_required
def dashboard(request):
	if(request.user.username=='admin'):
		print("admin")
		return render(request, 'recognition/admin_dashboard.html')
	else:
		print("not admin")
		return render(request,'recognition/employee_dashboard.html')

@login_required
def dashboard2(request):
	if(request.user.username=='admin'):
		print("admin")
		return render(request, 'recognition/ad_dashboard.html')
	else:
		print("not admin")
		return render(request,'recognition/StudentsLayout.html')

@login_required
def add_photos(request):
	if request.user.username!='admin':
		return redirect('not-authorised')
	if request.method=='POST':
		form=usernameForm(request.POST)
		data = request.POST.copy()
		username=data.get('username')
		if username_present(username):
			create_dataset(username)
			messages.success(request, f'Dataset Created')
			return redirect('add-photos')
		else:
			messages.warning(request, f'No such username found. Please register employee first.')
			return redirect('dashboard2')
	else:
			form=usernameForm()
			return render(request,'recognition/add_photos.html', {'form' : form})


#proxy detection code ~ mediapipe


def eye_aspect_ratio(eye):
    A = dist.euclidean(np.array([eye[1].x, eye[1].y]), np.array([eye[5].x, eye[5].y]))
    B = dist.euclidean(np.array([eye[2].x, eye[2].y]), np.array([eye[4].x, eye[4].y]))
    C = dist.euclidean(np.array([eye[0].x, eye[0].y]), np.array([eye[3].x, eye[3].y]))
    ear = (A + B) / (2.0 * C)
    return ear

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# Check if a thumbs up is detected
def is_thumbs_up(landmarks):
    thumb_tip = landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y
    thumb_mcp = landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP].y
    index_finger_mcp = landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y
    return thumb_tip < thumb_mcp and thumb_tip < index_finger_mcp

# Blink detection logic
def is_blinking(ear_history, blink_threshold=0.25):
    return sum(ear < blink_threshold for ear in ear_history) >= 3  # Adjust the threshold as needed
def mark_your_attendance(request):
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor('face_recognition_data/shape_predictor_68_face_landmarks.dat')
    svc_save_path = "face_recognition_data/svc.sav"

    with open(svc_save_path, 'rb') as f:
        svc = pickle.load(f)

    fa = FaceAligner(predictor, desiredFaceWidth=96)
    encoder = LabelEncoder()
    encoder.classes_ = np.load('face_recognition_data/classes.npy')

    # Initialize attendance and blink tracking
    count = {encoder.inverse_transform([i])[0]: 0 for i in range(len(encoder.classes_))}
    present = {encoder.inverse_transform([i])[0]: False for i in range(len(encoder.classes_))}
    present_users = []
    updated_users = []

    blink_counter = 0  # Counter for blinks to activate hand detection
    blink_threshold = 5  # Set threshold for required blinks
    ear_history = []  # To store recent EAR values
    display_messages = {}  # Store display messages for OpenCV

    vs = VideoStream(src=0).start()

    with mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7) as hands:
        while True:
            frame = vs.read()
            frame = imutils.resize(frame, width=800)
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector(gray_frame, 0)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            for face in faces:
                (x, y, w, h) = face_utils.rect_to_bb(face)
                face_aligned = fa.align(frame, gray_frame, face)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                (pred, prob) = predict(face_aligned, svc)

                if pred != [-1]:
                    person_name = encoder.inverse_transform(np.ravel([pred]))[0]
                    count[person_name] += 1

                    # Blink detection
                    landmarks = predictor(gray_frame, face)
                    leftEye = [landmarks.part(i) for i in range(36, 42)]
                    rightEye = [landmarks.part(i) for i in range(42, 48)]
                    leftEAR = eye_aspect_ratio(leftEye)
                    rightEAR = eye_aspect_ratio(rightEye)
                    ear = (leftEAR + rightEAR) / 2.0

                    # Update EAR history
                    ear_history.append(ear)
                    if len(ear_history) > 3:
                        ear_history.pop(0)

                    # Check if the person is blinking
                    if is_blinking(ear_history):
                        blink_counter += 1

                    # Logic to mark attendance only after enough blinks and thumbs up
                    if blink_counter >= blink_threshold:
                        results = hands.process(rgb_frame)
                        if results.multi_hand_landmarks:
                            for hand_landmarks in results.multi_hand_landmarks:
                                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                                if is_thumbs_up(hand_landmarks):
                                    if not present[person_name]:  # Only mark if not already marked
                                        present[person_name] = True
                                        present_users.append(person_name)

                                        # Update attendance in DB - marking IN
                                        if update_attendance_in_db_in({person_name: True}):
                                            updated_users.append(person_name)  # Successful mark
                                            display_messages[person_name] = time.time()
                                            update_attendance_in_db_in(present)
                                        else:
                                            print(f"Failed to mark {person_name} as present.")

                    # Display user name and probability
                    cv2.putText(frame, f"{person_name} {prob[0] * 100:.2f}%", (x + 6, y + h - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                else:
                    cv2.putText(frame, "unknown", (x + 6, y + h - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Display messages for users marked present
            for idx, person_name in enumerate(updated_users):
                cv2.putText(frame, f"{person_name} marked present", (50, 50 + idx * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("Mark Attendance - Press q to exit", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    vs.stop()
    cv2.destroyAllWindows()

    # Show success messages in Django
    for user in updated_users:
        messages.success(request, f'{user} marked present successfully!')

    update_attendance_in_db_out(present)
    
    return redirect('home')




def mark_your_attendance_out(request):
	detector = dlib.get_frontal_face_detector()	
	predictor = dlib.shape_predictor('face_recognition_data/shape_predictor_68_face_landmarks.dat')   #Add path to the shape predictor ######CHANGE TO RELATIVE PATH LATER
	svc_save_path="face_recognition_data/svc.sav"	
	with open(svc_save_path, 'rb') as f:
			svc = pickle.load(f)
	fa = FaceAligner(predictor , desiredFaceWidth = 96)
	encoder=LabelEncoder()
	encoder.classes_ = np.load('face_recognition_data/classes.npy')
	faces_encodings = np.zeros((1,128))
	no_of_faces = len(svc.predict_proba(faces_encodings)[0])
	count = dict()
	present = dict()
	log_time = dict()
	start = dict()
	for i in range(no_of_faces):
		count[encoder.inverse_transform([i])[0]] = 0
		present[encoder.inverse_transform([i])[0]] = False
	vs = VideoStream(src=0).start()
	sampleNum = 0
	while(True):		
		frame = vs.read()
		frame = imutils.resize(frame ,width = 800)
		gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		faces = detector(gray_frame,0)
		for face in faces:
			#print("INFO : inside for loop")
			(x,y,w,h) = face_utils.rect_to_bb(face)
			face_aligned = fa.align(frame,gray_frame,face)
			cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),1)
			(pred,prob)=predict(face_aligned,svc)
			if(pred!=[-1]):				
				person_name=encoder.inverse_transform(np.ravel([pred]))[0]
				pred=person_name
				if count[pred] == 0:
					start[pred] = time.time()
					count[pred] = count.get(pred,0) + 1
				if count[pred] == 4 and (time.time()-start[pred]) > 1.5:
					count[pred] = 0
				else:
				#if count[pred] == 4 and (time.time()-start) <= 1.5:
					present[pred] = True
					log_time[pred] = datetime.datetime.now()
					count[pred] = count.get(pred,0) + 1
					print(pred, present[pred], count[pred])
				cv2.putText(frame, str(person_name)+ str(prob), (x+6,y+h-6), cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1)
			else:
				person_name="unknown"
				cv2.putText(frame, str(person_name), (x+6,y+h-6), cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1)
		cv2.imshow("Mark Attendance- Out - Press q to exit",frame)
		key=cv2.waitKey(1) & 0xFF
		if(key==ord("q")):
			break
	vs.stop()
	cv2.destroyAllWindows()
	update_attendance_in_db_out(present)
	return redirect('home')
 

@login_required
def train(request):
    if request.user.username != 'admin':
        return redirect('not-authorised')

    training_dir = 'face_recognition_data/training_dataset'
    count = 0
    for person_name in os.listdir(training_dir):
        curr_directory = os.path.join(training_dir, person_name)
        if not os.path.isdir(curr_directory):
            continue
        for imagefile in image_files_in_folder(curr_directory):
            count += 1

    X = []
    y = []

    # Check if the model should be retrained
    retrain = request.method == 'POST'

    # If retraining, we skip loading the existing model
    if not retrain:
        svc_save_path = "face_recognition_data/svc.sav"
        if os.path.exists(svc_save_path):
            messages.success(request, 'Model already trained. Loading existing model.')
            with open(svc_save_path, 'rb') as f:
                svc = pickle.load(f)
            return render(request, "recognition/train.html")  # Adjust as needed

    # Training process
    for person_name in os.listdir(training_dir):
        print(str(person_name))
        curr_directory = os.path.join(training_dir, person_name)
        if not os.path.isdir(curr_directory):
            continue
        for imagefile in image_files_in_folder(curr_directory):
            print(str(imagefile))
            image = cv2.imread(imagefile)
            try:
                X.append((face_recognition.face_encodings(image)[0]).tolist())
                y.append(person_name)
            except Exception as e:
                print(f"Error processing {imagefile}: {e}")
                print("Removed invalid image.")
                os.remove(imagefile)

    targets = np.array(y)
    encoder = LabelEncoder()
    encoder.fit(y)
    y = encoder.transform(y)
    X1 = np.array(X)
    print("Shape of training data: " + str(X1.shape))

    # Save the classes and train the model
    np.save('face_recognition_data/classes.npy', encoder.classes_)
    svc = SVC(kernel='linear', probability=True)
    svc.fit(X1, y)

    # Save the trained model
    with open("face_recognition_data/svc.sav", 'wb') as f:
        pickle.dump(svc, f)

    # Visualize the training data (optional)
    vizualize_Data(X1, targets)

    messages.success(request, 'Training Complete.')
    return render(request, "recognition/train.html")

@login_required
def not_authorised(request):
	return render(request,'recognition/not_authorised.html')

@login_required
def view_attendance_home(request):
	total_num_of_emp=total_number_employees()
	emp_present_today=employees_present_today()
	this_week_emp_count_vs_date()
	last_week_emp_count_vs_date()
	return render(request,"recognition/view_attendance_home.html", {'total_num_of_emp' : total_num_of_emp, 'emp_present_today': emp_present_today})

@login_required
def view_attendance_date(request):
	if request.user.username!='admin':
		return redirect('not-authorised')
	qs=None
	time_qs=None
	present_qs=None

	if request.method=='POST':
		form=DateForm(request.POST)
		if form.is_valid():
			date=form.cleaned_data.get('date')
			print("date:"+ str(date))
			time_qs=Time.objects.filter(date=date)
			present_qs=Present.objects.filter(date=date)
			if(len(time_qs)>0 or len(present_qs)>0):
				qs=hours_vs_employee_given_date(present_qs,time_qs)
				return render(request,'recognition/view_attendance_date.html', {'form' : form,'qs' : qs })
			else:
				messages.warning(request, f'No records for selected date.')
				return redirect('view-attendance-date')
	else:
			form=DateForm()
			return render(request,'recognition/view_attendance_date.html', {'form' : form, 'qs' : qs})

@login_required
def view_attendance_employee(request):
	if request.user.username!='admin':
		return redirect('not-authorised')
	time_qs=None
	present_qs=None
	qs=None
	if request.method=='POST':
		form=UsernameAndDateForm(request.POST)
		if form.is_valid():
			username=form.cleaned_data.get('username')
			if username_present(username):	
				u=User.objects.get(username=username)
				time_qs=Time.objects.filter(user=u)
				present_qs=Present.objects.filter(user=u)
				date_from=form.cleaned_data.get('date_from')
				date_to=form.cleaned_data.get('date_to')				
				if date_to < date_from:
					messages.warning(request, f'Invalid date selection.')
					return redirect('view-attendance-employee')
				else:
					time_qs=time_qs.filter(date__gte=date_from).filter(date__lte=date_to).order_by('-date')
					present_qs=present_qs.filter(date__gte=date_from).filter(date__lte=date_to).order_by('-date')					
					if (len(time_qs)>0 or len(present_qs)>0):
						qs=hours_vs_date_given_employee(present_qs,time_qs,admin=True)
						return render(request,'recognition/view_attendance_employee.html', {'form' : form, 'qs' :qs})
					else:
						messages.warning(request, f'No records for selected duration.')
						return redirect('view-attendance-employee')
			else:
				print("invalid username")
				messages.warning(request, f'No such username found.')
				return redirect('view-attendance-employee')
	else:
			form=UsernameAndDateForm()
			return render(request,'recognition/view_attendance_employee.html', {'form' : form, 'qs' :qs})

@login_required
def view_my_attendance_employee_login(request):
	if request.user.username=='admin':
		return redirect('not-authorised')
	qs=None
	time_qs=None
	present_qs=None
	if request.method=='POST':
		form=DateForm_2(request.POST)
		if form.is_valid():
			u=request.user
			time_qs=Time.objects.filter(user=u)
			present_qs=Present.objects.filter(user=u)
			date_from=form.cleaned_data.get('date_from')
			date_to=form.cleaned_data.get('date_to')
			if date_to < date_from:
					messages.warning(request, f'Invalid date selection.')
					return redirect('view-my-attendance-employee-login')
			else:
					time_qs=time_qs.filter(date__gte=date_from).filter(date__lte=date_to).order_by('-date')
					present_qs=present_qs.filter(date__gte=date_from).filter(date__lte=date_to).order_by('-date')
					if (len(time_qs)>0 or len(present_qs)>0):
						qs=hours_vs_date_given_employee(present_qs,time_qs,admin=False)
						return render(request,'recognition/view_my_attendance_employee_login.html', {'form' : form, 'qs' :qs})
					else:
						messages.warning(request, f'No records for selected duration.')
						return redirect('view-my-attendance-employee-login')
	else:
			form=DateForm_2()
			return render(request,'recognition/view_my_attendance_employee_login.html', {'form' : form, 'qs' :qs})