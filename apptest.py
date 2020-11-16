from flask import Flask
from flask import Flask, flash, redirect, render_template, request, session, abort
import os
from flask import Flask, jsonify
import json
import re
import boto3
from boto3.dynamodb.conditions import Key, Attr
import aws_controller
from botocore.exceptions import ClientError
import aws_appt
import zoomtest_post
import password_strength
import email_validator
from email_validator import validate_email, EmailNotValidError, EmailSyntaxError, EmailUndeliverableError
from password_strength import PasswordPolicy
from passlib.context import CryptContext


#from aws_appt import getAllApptsFromUsername, returnAllPatients, getAcctFromUsername
#from zoomtest_post import updateMtg,createMtg,getMtgFromMtgID, getMtgsFromUserID,getUserFromEmail,deleteMtgFromID

app = Flask(__name__)

dynamo_client = boto3.client('dynamodb')
takenUsernames = aws_appt.returnAllPatients()
patientList = aws_appt.searchPatientList()

patientPages = []
currPg=0

@app.route('/get-items')
def get_items():
    return jsonify(aws_controller.get_items())

@app.route('/')
def home():
    if not (session.get('logged_in_p') or session.get('logged_in_d')):
        return render_template('login.html', errorMsg="")
    else:
        return displayLoggedInHome()

@app.route('/homepage')
def displayLoggedInHome():
    if(session.get('logged_in_d')):
        docStatus = 'doctor'
        return render_template('homePageDr.html',docStat = docStatus,name=session['name'])
    else:
        docStatus = 'patient'
        return render_template('homePage.html',docStat = docStatus,name=session['name'])

        #name of logged in person printed
        #doctor/patient

@app.route('/login', methods=['POST','GET'])
def check_login():
    dynamodb = boto3.resource("dynamodb", region_name='us-east-1', endpoint_url="http://localhost:4000")

    table = dynamodb.Table('YourTestTable')
    pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        default="pbkdf2_sha256",
        pbkdf2_sha256__default_rounds=30000
    )
    try:
        response = dynamo_client.get_item(TableName= 'users',
            Key={
                'username': {"S":request.form['username']}                
            }
        )
        try:
            test = response.get('Item').get('password')
        except:
            return render_template('login.html', errorMsg="Incorrect username or password.")
        if( False==(pwd_context.verify(request.form['password'], response.get('Item').get('password').get('S')))):
            print("WRONG PASSWORD")
            return render_template('login.html', errorMsg="Incorrect username or password.")
            #return home()
        formEmail = response.get('Item').get('email').get('S')
        docStatus = str(response.get('Item').get('docStatus').get('S'))
        if(docStatus=='doctor'):
            session['logged_in_d']=True
            session['logged_in_p']=False
        else:
            session['logged_in_p'] = True
            session['logged_in_d']=False
        session['username'] = request.form['username']
        session['name'] = str(response.get('Item').get('fname').get('S'))+" "+str(response.get('Item').get('lname').get('S'))
    except ClientError as e:
        print(e.response['Error']['Message'])
    return home()

@app.route('/registerrender', methods=['POST','GET'])
def regPg():
    return render_template('register.html')

@app.route('/register', methods=['POST','GET'])
def new_register():
    response = dynamo_client.get_item(TableName= 'users',
        Key={
            'username': {"S":request.form['username']}                
        }
    )
    try:
        test = response.get('Item').get('password')
        return render_template('register.html',
                               errorMsg="Username is already taken. Please use a different one.",
                               username = request.form['username'],
                               password = request.form['password'],
                               email = request.form['email'],
                               fname = request.form['fname'],
                               lname = request.form['lname']
                               )
    except:

        policy = PasswordPolicy.from_names(
            length=8,  # min length: 8
            uppercase=1,  # need min. 2 uppercase letters
            numbers=1  # need min. 2 digits
            )
        if len(request.form['fname'])<2 or len(request.form['lname'])<2:
            return render_template('register.html',
                                   errorMsg="First and last name must have at least 2 characters.",
                                    username = request.form['username'],
                                   password = request.form['password'],
                                   email = request.form['email'],
                                   fname = request.form['fname'],
                                   lname = request.form['lname']
                                   )
##PASSWORD STRENGTH
        isEnough = policy.test(str(request.form['password']))
        if len(isEnough):
            return render_template('register.html',
                                   errorMsg="Password must be min length 8, 1 upper case, and 1 number.",
                                    username = request.form['username'],
                                   password = request.form['password'],
                                   email = request.form['email'],
                                   fname = request.form['fname'],
                                   lname = request.form['lname']
                                   )
        try:
            formEmail = request.form['email']
            valid = validate_email(formEmail)
        except:
            return render_template('register.html',
                                   errorMsg="Invalid email format or domain.",
                                    username = request.form['username'],
                                   password = request.form['password'],
                                   email = request.form['email'],
                                   fname = request.form['fname'],
                                   lname = request.form['lname']
                                   ) 
        pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        default="pbkdf2_sha256",
        pbkdf2_sha256__default_rounds=30000
        )
        response = dynamo_client.put_item(TableName= 'users',
           Item={
                'username': {"S":request.form['username']},
                'password': {"S":pwd_context.hash(request.form['password'])},
                'email': {"S":request.form['email']},
                'fname':{"S":request.form['fname']},
                'lname':{"S":request.form['lname']},
                'docStatus':{"S":request.form['docStatus']}
            }
           )
        takenUsernames.append(request.form['username'])
   

        if(request.form['docStatus']=='doctor'):
            session['logged_in_d']=True
            session['logged_in_p']=False
        else:
            session['logged_in_p'] = True
            session['logged_in_d']=False
        session['username'] = request.form['username']
        session['name'] = request.form['fname']+" "+request.form['lname']
        
        return displayLoggedInHome()

@app.route('/usernamecheck', methods=['POST','GET'])
def usernamecheck():
    #print("in UC", request)
    text = request.args.get('jsdata')
    if(text in takenUsernames):
        text=""
        return 'USERNAME TAKEN'
##    no _ or . at the end
##    allowed characters = [a-zA-Z0-9._] (NOT /*$#@+=?><,;':%^&())
##    no __ or _. or ._ or .. inside
##    no _ or . at the beginning
##    username is 5-20 characters long
#
    if not(re.match("^(?=.{5,20}$)(?![_.])(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$", text)):
        text=""
        return "5-20 characters. No spaces. Cannot start/end with punctuation. Cannot contain /*$#@+=?><,;':%^&()"   
    return ""

@app.route('/emailCheck', methods=['POST','GET'])
def emailcheck():
    text = request.args.get('jsdata')
    try:
        valid = validate_email(text)
        text = ""
        return ""
    except EmailNotValidError as e:
        if(type(e)==EmailSyntaxError):
            text=""
            return "Incorrectly formatted email address."
        if(type(e)==EmailUndeliverableError):
            text=""
            return "Invalid domain."
        
        text = ""
        return str(e)

@app.route('/nameLengthCheck', methods=['POST','GET'])
def namecheck():
    #print("in UC", request)
    text = request.args.get('jsdata')
    if(len(text)<2):
        text=""
        return 'First and last name need 2+ characters'
    return ""

@app.route('/pwStrengthCheck', methods=['POST','GET'])
def pwStrCheck():
    #print(request.form['jsdata'])
    #print(request.args)
    text = request.form.get('jsdata')
    policy = PasswordPolicy.from_names(
            length=8,  # min length: 8
            uppercase=2,  # need min. 2 uppercase letters
            numbers=2  # need min. 2 digits
            )
##PASSWORD STRENGTH
    isEnough = policy.test(str(text))
    text=""
    if len(isEnough):
        #print(type(isEnough[0]))
        if len(isEnough)==1:
            if type(isEnough[0])==password_strength.tests.Length:
                return "<8 characters"
            elif type(isEnough[0])==password_strength.tests.Uppercase:
                return "<2 capital letters"
            elif type(isEnough[0])==password_strength.tests.Numbers: 
                return "<2 digits"
        elif len(isEnough)==2: #any 2 combinationsS
            if type(isEnough[0])==password_strength.tests.Length:
                if type(isEnough[1])==password_strength.tests.Uppercase:
                    return "<8 characters\n<2 capital letters"
                elif type(isEnough[1])==password_strength.tests.Numbers: 
                    return "<8 characters\n<2 digits"
            elif type(isEnough[0])==password_strength.tests.Uppercase:
                if type(isEnough[1])==password_strength.tests.Numbers: 
                    return "<2 capital letters\n<2 digits"
                elif type(isEnough[1])==password_strength.tests.Length: 
                    return "<2 capital letters\n<8 characters"
            elif type(isEnough[0])==password_strength.tests.Numbers: 
                if type(isEnough[1])==password_strength.tests.Uppercase:
                    return "<2 digits\n<2 capital letters"
                elif type(isEnough[1])==password_strength.tests.Length: 
                    return "<2 digits\n<8 characters"
        else: #all 3
            return "<8 characters\n<2 capital letters\n<2 digits"
    else:
        return ""

def accessDenied():
    return render_template('accessDenied.html')

@app.route('/createrender', methods=['POST','GET'])
def createPg():
    if session['logged_in_p']:
        return accessDenied()
    listStr = aws_appt.returnAllPatients()
    listStr.sort()
    return render_template('create_mtg.html',
                           errorMsg = "",
                           options=listStr)

@app.route('/createrender/<username>', methods=['POST','GET'])
def createWithUsername(username):
    if session['logged_in_p']:
        return accessDenied()
    listStr = []
    listStr.append(username)
    return render_template('create_mtg.html',
                           errorMsg = "",
                           options=listStr)

@app.route('/create_search', methods=['POST','GET'])
def createUserSearch():
    jsonSuggest = []
    query = request.args.get('query')
    listPatients=patientList#takenUsernames
    for username in listPatients:
        if(query in username):
            jsonSuggest.append({'value':username,'data':username.split(" - ")[0]})#'<div style="background-color:#cccccc; text-align:left; vertical-align: middle; padding:20px 47px;">'+username+'<div>'})
        #suggestions = [{'value': 'joe','data': 'joe'}, {'value': 'jim','data': 'jim'}]
    return jsonify({"suggestions":jsonSuggest})

@app.route('/createmtg', methods=['POST','GET'])
def create_mtg():
    if session['logged_in_p']:
        return accessDenied()
    time = str(request.form['day'])+'T'+ str(request.form['time'])+':00Z'
    #need to ensure that what is entered is either autocorrect, or valid
    if len(request.form['patientUser'].split(" - "))>1:
        username = request.form['patientUser'].split(" - ")[0]
        jsonResp, awsResp = zoomtest_post.createMtg(str(request.form['mtgname']), time,str(request.form['password']),session['username'], username)
#session['username'] == doctor
    else:
        jsonResp, awsResp = zoomtest_post.createMtg(str(request.form['mtgname']), time,str(request.form['password']),session['username'], request.form['patientUser'])
    date=time[:10]
    finalStr = ""
    if awsResp!="Successfully inserted the appt into the database.":
        listStr = aws_appt.returnAllPatients()
        listStr.sort()
        return render_template('create_mtg.html',
                               errorMsg = awsResp,
                               options=listStr)
#ADD PATIENT FIELD
    
    else:
        return render_template('apptDetail.html',
                               mtgnum=str(jsonResp.get("id")),
                               doctor =session['username'],
                               patient = request.form['patientUser'],
                               mtgname=str(jsonResp.get("topic")),
                               mtgtime=str(time[11:-1]),
                               mtgdate=str(date))
    ##make a joinURL field on this AND the mtg detail page


##CALENDAR FAILS TO DISPLAY FOR THE FOLLOWING CONDITIONS:
    #{"title": "HELP", "start": "2020-09-27T00:53:00", "end": "2020-09-27T1:53:00", "url": "/showmtgdetail/75274348158"}
    #^^^^ END OR START TIME NOT HAVING 2 PLACES (NOT LEADING WITH A 0 WHEN 1 DIGIT TIME)
    #{"title": "asl", "start": "2020-09-21T14:46:00:00", "end": "2020-09-21T15:46:00:00", "url": "/showmtgdetail/75141590110"}
    #^^^^ HAVING AN EXTRA SET OF 00 AFTER THE TIME
#DO ERROR CATCHING ********************************************
    #edited meetings have the extra :00? -> just chop it off every time? or update it in the aws dtb?
    #just tack on the 0 when it's missing

@app.route('/data')
def return_data():
    arrOfMtgs =aws_appt.getAllApptsFromUsername(session['username'])
    #[{ "title": "Meeting",
    #"start": "2014-09-12T10:30:00-05:00",
    #"end": "2014-09-12T12:30:00-05:00",
    #"url":"absolute or relative?"},{...}]
    
    mtgList = []
    finalStr = ""
    for item in arrOfMtgs:
        time = str(item.get("start_time"))
        mtgid = str(item.get("mtgid"))
        if(time[-1]=='Z'):
            time = time[:-1] #takes off the 'z'
        if(len(time[11:].split(":"))>=4): #catches any times with extra :00s
            time = time[:19]
        end_time = int(float(time[11:13]))+1
        strend = time[:11]+str(end_time)+time[13:]
        if(end_time<=9): #catches any times <9 that would be single digit
            strend = time[:11]+"0"+str(end_time)+time[13:]
        
        mtgObj = {"title":str(item.get("mtgName")), "start": time, "end":strend, "url":("/showmtgdetail/"+mtgid)}
        mtgList.append(mtgObj)
    #BADDDD (change this)
    with open('appts.json', 'w') as outfile:
        json.dump(mtgList, outfile)
    with open('appts.json', "r") as input_data:
        #print(input_data.read())
        return input_data.read()    

@app.route('/showmtgdetail/<mtgid>', methods=['POST','GET'])
def show_mtgdetail(mtgid):     # TODO ---(make this calendar) Or when the calendar is clicked, have it call the show mtgs and format each mtg to show up correctly
    jsonResp,awsResp = zoomtest_post.getMtgFromMtgID(str(mtgid))
    time=str(jsonResp.get("start_time"))
    #split and display
    date=time[:10]
    docUser = awsResp.get('Item').get('doctor').get('S')
    patUser = awsResp.get('Item').get('patient').get('S')
    if(session.get('logged_in_p')):
        return render_template('apptDetail.html',
                               mtgnum=mtgid,
                               doctor=docUser,
                               patient = session['username'],
                               mtgname=str(jsonResp.get("topic")),
                               mtgtime=str(time[11:-1]),
                               mtgdate=str(date))
    elif(session.get('logged_in_d')):
        return render_template('apptDetailDrOptions.html',
                       mtgnum=mtgid,
                       doctor =docUser,
                       patient = patUser,
                       mtgname=str(jsonResp.get("topic")),
                       mtgtime=str(time[11:-1]),
                       mtgdate=str(date))

@app.route("/editrender/", methods=['POST','GET'])
def editPgFromID():
    mtgid = str(request.form['mtgnum'])
    if session['logged_in_p']:
        return accessDenied()
    jsonResp, awsResp = zoomtest_post.getMtgFromMtgID(request.form['mtgnum'])

    #mtgname, pword, mtgtime, mtgdate
    time=str(jsonResp.get("start_time"))
    #split and display
    date=time[:10]

    return render_template('edit.html',
                           mtgnum=mtgid,
                           mtgname=str(jsonResp.get("topic")),
                           pword=str(jsonResp.get("password")),
                           mtgtime=str(time[11:-1]),
                           mtgdate=str(date))


@app.route("/editmtg", methods=['POST','GET'])
def editSubmit():
    if session['logged_in_p']:
        return accessDenied()
    time = str(request.form['day'])+'T'+ str(request.form['time'])+':00Z'
    jsonResp = zoomtest_post.updateMtg(str(request.form['mtgnum']),str(request.form['mtgname']), time,str(request.form['password']))

    jsonResp,awsResp = zoomtest_post.getMtgFromMtgID(str(request.form['mtgnum']))
    time=str(jsonResp.get("start_time"))

    #split and display
    date=time[:10]
    docUser = awsResp.get('Item').get('doctor').get('S')
    patUser = awsResp.get('Item').get('patient').get('S')
    return render_template('apptDetailDrOptions.html',
                       mtgnum=str(request.form['mtgnum']),
                       doctor =docUser,
                       patient = patUser,
                       mtgname=str(jsonResp.get("topic")),
                       mtgtime=str(time[11:-1]),
                       mtgdate=str(date))

@app.route('/acctdetails', methods=['POST','GET'])
def acct_details():     
    response = aws_appt.getAcctFromUsername(str(session['username']))
    name = str(response.get('Item').get('fname').get('S'))+" "+str(response.get('Item').get('lname').get('S'))
    return render_template('ownAcctPg.html', 
                           username=session['username'],
                           docstatus=response.get('Item').get('docStatus').get('S'),
                           nm=name,
                           email=response.get('Item').get('email').get('S')
                           )

@app.route('/acctEditrender/', methods=['POST','GET'])
def editAcctRender():
    awsResp = aws_appt.getAcctFromUsername(str(request.form['username']))
    return render_template('editProfile.html',
                           errorMsg="",
                           username=session['username'],
                           pword1="",
                           pwordNew1="",
                           pwordNew2="",
                           email=awsResp.get('Item').get('email').get('S'),
                           fname=awsResp.get('Item').get('fname').get('S'),
                           lname=awsResp.get('Item').get('lname').get('S')
                           )

@app.route('/editacct', methods=['POST','GET'])
def editAcctDetails():
    oldPw = str(request.form['pword1'])
    newPw1 = str(request.form['pwordNew1'])
    newPw2 = str(request.form['pwordNew2'])
    awsResp = aws_appt.getAcctFromUsername(str(request.form['username']))
    pwUpdate = False
    errMsg=""
    errFlag=False
    if(oldPw=="" and newPw1=="" and newPw2==""):
        #no password change is happening
        pwUpdate=False
        print("NO PASSWORD UPDATE")
    else:
        policy = PasswordPolicy.from_names(
            length=8,  # min length: 8
            uppercase=1,  # need min. 2 uppercase letters
            numbers=1  # need min. 2 digits
            )
        isEnough = policy.test(newPw1)
        pwUpdate=True
        errMsg=""
        errFlag=False
#FIRST NEED TO VALIDATE THAT THE OLD PASSWORD IS RIGHT!!!
        oldPassw = awsResp.get('Item').get('password').get('S')
        if oldPw!=oldPassw:
            errFlag=True
            errMsg="Password entered does not match the acct's password."
        elif oldPw==newPw1 and newPw1==newPw2:
            errFlag=True
            errMsg="New password has to be different from old password."
        elif newPw1!=newPw2:
            errFlag=True
            errMsg="New passwords did not match"
        #if it gets here, we know the new pw != old pw and new pws match
        elif len(isEnough):
            errFlag=True
            errMsg="New password must be min length 8, 1 upper case, and 1 number."

    if(errFlag):
        return render_template('editProfile.html',
                           errorMsg=errMsg,
                           username=session['username'],
                           pword1="",
                           pwordNew1="",
                           pwordNew2="",
                           email=awsResp.get('Item').get('email').get('S'),
                           fname=awsResp.get('Item').get('fname').get('S'),
                           lname=awsResp.get('Item').get('lname').get('S')
                           )
    #if the password is fine, check names and email formatting
    if len(request.form['fname'])<2 or len(request.form['lname'])<2:
        #awsResp = aws_appt.getAcctFromUsername(str(request.form['username']))
        return render_template('editProfile.html',
                           errorMsg="First and last name must have at least 2 characters.",
                           username=session['username'],
                           pword1="",
                           pwordNew1="",
                           pwordNew2="",
                           email=awsResp.get('Item').get('email').get('S'),
                           fname=awsResp.get('Item').get('fname').get('S'),
                           lname=awsResp.get('Item').get('lname').get('S')
                           )
    emailAddr=str(request.form['email'])
    if(len(emailAddr.split("@"))!=2):
        return render_template('editProfile.html',
                           errorMsg="Invalid email address format.",
                           username=session['username'],
                           pword1="",
                           pwordNew1="",
                           pwordNew2="",
                           email=awsResp.get('Item').get('email').get('S'),
                           fname=awsResp.get('Item').get('fname').get('S'),
                           lname=awsResp.get('Item').get('lname').get('S')
                           )
    #if it's gotten past here, we know password is fine (or not being updated), email is fine, f and l name are fine
    if(pwUpdate==False):
        response = aws_appt.updateUserAcct(session['username'], str(request.form['email']),request.form['fname'], request.form['lname'], awsResp.get('Item').get('password').get('S'))
    else:
        response = aws_appt.updateUserAcct(session['username'], str(request.form['email']),request.form['fname'], request.form['lname'], newPw1)
    session['name']=str(request.form['fname'])+" "+str(request.form['lname'])
    return acct_details()



@app.route('/patients/<username>', methods=['POST','GET'])
def patientAcct(username):
    ##dr will not be given the option to edit any details
    ##this is where medical details will eventually be rendered
    print("PATIENT USER")
    response = aws_appt.getAcctFromUsername(str(username))
    name = str(response.get('Item').get('fname').get('S'))+" "+str(response.get('Item').get('lname').get('S'))
    return render_template('patientAcctDetails.html', 
                           username=username,
                           docstatus=response.get('Item').get('docStatus').get('S'),
                           nm=name,
                           email=response.get('Item').get('email').get('S')
                           )

@app.route('/patients', methods=['POST','GET'])
def list_patients():
    listStr = aws_appt.returnAllPatients()
    listStr.sort()
    patientPages = []
    currPg=0
    return displayPagedSearch(listStr)
    #return render_template('picture.html', options=listStr) #THIS

@app.route('/searchpgrender', methods=['POST','GET'])
def search_patients():
    return render_template('searchPg.html')

@app.route('/searchResult', methods=['POST','GET'])
def search_page():
    query = request.form['names']
    if(query==""): #if the form is empty, return all of the usernames
        listStr = aws_appt.returnAllPatients()
##        listStr = ["alpha","beta","chi","delta",
##              "eta","epsilon","gamma","iota",
##              "kappa", "lambda","mu","nu",
##              "omicron","omega","pi","phi",
##              "psi","rho","sigma","tau",
##              "theta", "upsilon", 'xi',"zeta"]
        listStr.sort()
        patientPages = []
        currPg=0
        return displayPagedSearch(listStr)
        #return render_template('picture.html', options=listStr) #THIS
    
    actualUsername = (query.split(" - "))[0] #username - last name, first name
    response = aws_appt.getAcctFromUsername(actualUsername)
    if(len(query.split(" - "))==2 and len(response)==2):
            #if the username exists and the user used the autocomplete -> take them to the account page directly
        name = str(response.get('Item').get('fname').get('S'))+" "+str(response.get('Item').get('lname').get('S'))
        return render_template('patientAcctDetails.html', 
                           username=actualUsername,
                           docstatus=response.get('Item').get('docStatus').get('S'),
                           nm=name,
                           email=response.get('Item').get('email').get('S')
                           )
    
    jsonSuggest=[]
    listStr=[]
    listPatients=patientList
    for username in listPatients:
        if(query in username):
            jsonSuggest.append({'value':username,'data':username})
            actualUsername = (username.split(" - "))[0]
            listStr.append(actualUsername)
##    listStr = ["alpha","beta","chi","delta",
##              "eta","epsilon","gamma","iota",
##              "kappa", "lambda","mu","nu",
##              "omicron","omega","pi","phi",
##              "psi","rho","sigma","tau",
##              "theta", "upsilon", 'xi',"zeta"]
    listStr.sort()
    patientPages = []
    currPg=0
    return displayPagedSearch(listStr)
    #return render_template('picture.html', options=listStr) #THIS


def displayPagedSearch(patientList):
    #the PROBLEM is that the patientPages needs to be cleared every time this is called
    #but for some reason if it is cleared before appending, it is blank when nextPg() is triggered and tries to access the array
    #to be solved
   patientPages = []
   numPatientsOnPg = 5
    #print("1-->",patientPages)
   currPg=0
   numOfPages = 0
   if(len(patientList)>5):
       #patientPages = []
       numOfPages = (len(patientList)/numPatientsOnPg)+1
       position = 0
       tempList = []
       for item in patientList:
           tempList.append(item)
           position = position+1
           if(position==numPatientsOnPg):
               patientPages.append(tempList)
               position=0
               tempList=[]
       patientPages.append(tempList) #tacks on the last partial page
       #print("2-->",patientPages)
       result = ""
       for page in patientPages:
           for patient in page:
               result = result + str(patient)+","
           result = result[:-1] #take off the last ,
           result = result + "|"
       result = result[:-1] #take off the last |

               
       #<p>Results {{startResultNum}} - {{endResultNum}} / {{totalResultNum}} (Page {{currPgNum}})</p>
       return render_template('patPgn.html',
                              startResultNum=1,
                              endResultNum=numPatientsOnPg,
                              totalResultNum=len(patientList),
                              currPgNum=currPg+1,
                           options=patientPages[currPg],
                              fullPagesArr=result,
                           npgnum=currPg+1)
   else:
        #patientPages = []
        result = ""
        for patient in patientPages:
            result = result + str(patient)+","
        result = result[:-1] #take off the last ,
        #print("3-->",patientPages)
        patientPages.append(patientList)
        return render_template('patientPaging.html',
                            startResultNum=1,
                              endResultNum=len(patientList),
                              totalResultNum=len(patientList),
                              currPgNum=currPg+1,
                           options=patientList,
                            fullPagesArr=result)

       
@app.route('/page', methods=['POST','GET'])
def nextPg():
    numPatientsOnPg = 5
    pageStr = request.form['fullPagesArr']
    patientPages = []
    pages = pageStr.split("|")
    temp = []
    counter = 0
    for page in pages:
        for patient in page.split(","):
            temp.append(patient)
            counter = counter+1
        patientPages.append(temp)
        temp = []
    pageNum = len(patientPages)
    totalNumPatients = counter
    #print("4-->",patientPages)
    
    #rint(pageNum)
    try:
        #print(request.form['prev'])
        currPg = int(request.form['prev'])
    except:
        #print(request.form['next'])
        currPg = int(request.form['next'])
    #print("CurrPg",currPg)
    
    if(len(patientPages)==1):
        return render_template('patientPaging.html',
                                startResultNum=1,
                              endResultNum=numPatientsOnPg,
                              totalResultNum=totalNumPatients,
                              currPgNum=currPg+1,
                           options=patientPages[currPg],
                               fullPagesArr=pageStr)
    elif(currPg==0):
        return render_template('patPgn.html',
                                startResultNum=1,
                              endResultNum=numPatientsOnPg,
                              totalResultNum=totalNumPatients, 
                              currPgNum=currPg+1,
                           options=patientPages[currPg],
                               fullPagesArr=pageStr,
                           npgnum=currPg+1)
    elif(currPg==(pageNum-1)):
        return render_template('patPgp.html',
                                startResultNum=((currPg)*numPatientsOnPg)+1,##
                              endResultNum=totalNumPatients,## not +5
                              totalResultNum=totalNumPatients,
                              currPgNum=currPg+1,
                           options=patientPages[currPg],
                               fullPagesArr=pageStr,
                           ppgnum=currPg-1)
    else:
        return render_template('patPgnp.html',
                                startResultNum=((currPg)*numPatientsOnPg)+1, ##
                              endResultNum=((currPg)*numPatientsOnPg)+1+5, ##+5
                              totalResultNum=totalNumPatients,
                              currPgNum=currPg+1,
                           options=patientPages[currPg],
                               fullPagesArr=pageStr,
                           ppgnum=currPg-1,
                            npgnum=currPg+1)

    
#UNUSED
##@app.route("/search")
##def processSearch():
##    jsonSuggest = []
##    query = request.args.get('jsdata')
##    #query = request.args.get('query')
##    listPatients=patientList
##    num = 0
##    for username in listPatients:
##        if(query in username):
##            num+=1#'<div style="background-color:#cccccc; text-align:left; vertical-align: middle; padding:20px 47px;">'+username+'<div>'})
##        #suggestions = [{'value': 'joe','data': 'joe'}, {'value': 'jim','data': 'jim'}]
##    print("HERRRRRRRRRE")
##    return '<div class="error">BLACH</div>'#'<textarea style="height:'+str(num*25)+'px;"></textarea>'

@app.route("/search/<string:box>")
def process(box):
    jsonSuggest = []
    query = request.args.get('query')
    listPatients=patientList
    for username in listPatients:
        if(query in username):
            jsonSuggest.append({'value':username,'data':username})#'<div style="background-color:#cccccc; text-align:left; vertical-align: middle; padding:20px 47px;">'+username+'<div>'})
        #suggestions = [{'value': 'joe','data': 'joe'}, {'value': 'jim','data': 'jim'}]
    return jsonify({"suggestions":jsonSuggest})

@app.route('/showallmtgs', methods=['POST','GET'])
def show_mtg():
    return render_template("calendar.html")

#This is what is needed to be able to link to this page
#make a get method a part of the route
@app.route("/deleterender", methods=['POST','GET'])
def deletePg():
    if session['logged_in_p']:
        return accessDenied()
    return render_template('delete.html', mtg="")

@app.route("/deleteRenderNum/", methods=['POST','GET']) 
def deletePgNum():
    if session['logged_in_p']:
        return accessDenied()
    mtgid = str(request.form['mtgnum'])
    return render_template('delete.html', mtg=mtgid)


@app.route("/deletemtg", methods=['POST','GET'])
def deleteMtg():
    if session['logged_in_p']:
        return accessDenied()
    awsResp = aws_appt.getApptFromMtgId(str(request.form['mtgID']))
    try:
        if len(awsResp)>=1:
            zoomtest_post.deleteMtgFromID(str(request.form['mtgID']))
        return render_template('deleteConfirm.html', mtgnum=str(request.form['mtgID']))
    except:
        return "NO That is a bad meeting ID, please go back and try again<br><a href='/deleterender'>Delete</a>"
        

@app.route("/logout", methods=['POST','GET'])
def logout():
    session['logged_in_p'] = False
    session['logged_in_d'] = False
    return home()

if __name__ == "__main__":
    patientPages = []
    app.secret_key = os.urandom(12)
    app.run(debug=True,host='0.0.0.0', port=4000)
