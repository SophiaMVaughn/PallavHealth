
import mysql.connector
from mysql.connector import errorcode

from password_strength import PasswordPolicy
from passlib.context import CryptContext
import email_validator
from email_validator import validate_email, EmailNotValidError, EmailSyntaxError, EmailUndeliverableError
from datetime import date, datetime,timezone

config = {
  'host':'treeo-server.mysql.database.azure.com',
  'user':'treeo_master@treeo-server',
  'password':'Password1',
  'database':'treeohealthdb'
}
cnx = mysql.connector.connect(**config)
cursor = cnx.cursor()
cursor.execute("USE treeoHealthDB")

pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        default="pbkdf2_sha256",
        pbkdf2_sha256__default_rounds=30000
    )

def insertDoctor(username, password, email, fname, lname, drType, cursor, cnx):
    if(isUsernameTaken(username,cursor, cnx)):
        return "taken error"

    policy = PasswordPolicy.from_names(
            length=8,  # min length: 8
            uppercase=1,  # need min. 2 uppercase letters
            numbers=1  # need min. 2 digits
            )
    

    isEnough = policy.test(password)
    if len(isEnough)!=0:
        return "weak password"
    
    try:
        valid = validate_email(email)
    except:
        return "bad email or domain"

    if len(fname)<2 or len(lname)<2:
        return "short name error"

    pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        default="pbkdf2_sha256",
        pbkdf2_sha256__default_rounds=30000
    )

    formatInsert = ("INSERT INTO doctorTable "
                   "(username, password,email,fname,"
                    "lname,drType,creationDate) "
                   "VALUES (%s, %s,%s, %s,%s, %s,%s)") #NOTE: use %s even with numbers
    insertContent = (username, pwd_context.hash(password), email, fname, lname, drType, str(date.today().strftime("%B %d, %Y")))
    cursor.execute(formatInsert, insertContent)
    cnx.commit()

    return "success"



def insertPatient(username, password, email, fname, lname, cursor, cnx):
    if(isUsernameTaken(username,cursor, cnx)):
        return "taken error"

    policy = PasswordPolicy.from_names(
            length=8,  # min length: 8
            uppercase=1,  # need min. 2 uppercase letters
            numbers=1  # need min. 2 digits
            )
    

    isEnough = policy.test(password)
    if len(isEnough)!=0:
        return "weak password"
    
    try:
        valid = validate_email(email)
    except:
        return "bad email or domain"

    if len(fname)<2 or len(lname)<2:
        return "short name error"


    pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        default="pbkdf2_sha256",
        pbkdf2_sha256__default_rounds=30000
    )

    formatInsert = ("INSERT INTO patientTable "
                   "(username, password,email,fname,"
                    "lname,drOne, drTwo, drThree,creationDate) "
                   "VALUES (%s, %s,%s, %s,%s, %s,%s, %s,%s)") #NOTE: use %s even with numbers
    
        #their care team is not assigned at creation, so N/A
    insertContent = (username, pwd_context.hash(password), email, fname, lname, "N/A", "N/A", "N/A", str(date.today().strftime("%B %d, %Y")))
    cursor.execute(formatInsert, insertContent)
    cnx.commit()

    return "success"



def isUsernameTaken(username, cursor, cnx): #fix SQL DONE
        #the 2 queries need to have the same # of attributes in the select
    query = ("SELECT username FROM doctorTable WHERE username = %s" ) 
        #because the doctor table will always be smaller, always query it first
    cursor.execute(query, (username,))
    for item in cursor:
        return True #if this is a dr, if will not query the patientTable
    
    query = ("SELECT username FROM patientTable WHERE username = %s") 
    cursor.execute(query, (username, username)) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    for item in cursor:
        return True 
    
    return False #it was queried in both tables and neither matched


def checkUserLogin(username, pwrd, cursor, cnx): #fix SQL DONE
    
    pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        default="pbkdf2_sha256",
        pbkdf2_sha256__default_rounds=30000 #num of times it will hash before writing
    )
    
    query = ("SELECT username, password FROM doctorTable WHERE username = %s")
    cursor.execute(query, (username, ))
    for un, pw in cursor: #this loop will not be entered if it does not exist in the doctorDB
        if( True==(pwd_context.verify(pwrd, pw))):
            return True
        else: #because there can only be 1 match, this query can only be run 1 time max (not O(n^2))
            print("WRONG PASSWORD")
            return False
              
    query = ("SELECT username, password FROM patientTable WHERE username = %s")
    cursor.execute(query, (username, ))
    for un, pw in cursor: #this loop will not be entered if it does not exist in the patientDB
        if( True==(pwd_context.verify(pwrd, pw))):
            return True
        else:
            print("WRONG PASSWORD")
            return False
    
    
    print("bad username")
    return False
        
    # query = ("SELECT username, password FROM doctorTable WHERE username = %s")   
    # cursor.execute(query, (username, ))
    
    # for usern, password in cursor: #this loop will not be entered if it does not exist in the doctorDB
    #     if( False==(pwd_context.verify(pwrd, password))):
    #         print("WRONG PASSWORD")
    #         return False
    #     else:
    #         return True
    # print("bad username")
    # return False
    

def returnAllPatients(cursor, cnx): 
    query = ("SELECT username FROM patientTable")         #BETWEEN %s AND %s")
    cursor.execute(query) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    patientArr = []
    for un in cursor:
        patientArr.append(un[0])
    return patientArr

def searchPatientList(cursor, cnx):
    query = ("SELECT username, fname, lname FROM patientTable")         #BETWEEN %s AND %s")
    cursor.execute(query) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    patientArr = []
    for un,fn,ln in cursor:
        patientArr.append(str(un+" - "+ln+", "+fn))
    return patientArr

def allSearchUsers(cursor, cnx): #fix SQL DONE
    query = ("SELECT * "
             "FROM (SELECT username, fname, lname FROM patientTable) " 
             "UNION (SELECT username, fname, lname FROM doctorTable)") 
    cursor.execute(query) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    nameArr = []
    for un,fn,ln in cursor:
        tmp = str(un+" - "+ln+", "+fn)
        nameArr.append(tmp)

    return nameArr

def getCareTeamOfUser(username, cursor, cnx):
    query = ("SELECT drOne, drTwo, drThree FROM patientTable WHERE username = %s") 
    cursor.execute(query, (username, ))
    for d1, d2, d3 in cursor:
        return (d1, d2, d3)
    return 

def assignPatientCareTeam(patientUser, dr1User, dr2User, dr3User, cursor, cnx):
    currCare = getCareTeamOfUser(patientUser, cursor, cnx)
    if("N/A" in currCare): #if any of the drs are unassigned
        update_test = (
                "UPDATE patientTable SET drOne=%s, drTwo=%s, drThree=%s"
                "WHERE username = %s")
        cursor.execute(update_test, (dr1User, dr2User, dr3User, patientUser))
        cnx.commit()
        return "success"
    return

def searchDoctorList(cursor, cnx):
    query = ("SELECT username, fname, lname FROM doctorTable")         #BETWEEN %s AND %s")
    cursor.execute(query) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    docArr = []
    for un,fn,ln in cursor:
        tmp = str(un+" - "+ln+", "+fn)
        docArr.append(tmp)
    return docArr

def getDrTypeOfAcct(username, cursor, cnx):
    query = ("SELECT drType FROM doctorTable WHERE username=%s")
    cursor.execute(query, (username, ))
    for dr in cursor:
        return dr[0]
    return

def getAllDrDietician(cursor, cnx):
    query = ("SELECT username, fname, lname FROM doctorTable WHERE drType=%s")         #BETWEEN %s AND %s")
    cursor.execute(query, ("dietician",)) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    docArr = []
    for un,fn,ln in cursor:
        tmp = str(un+" - "+ln+", "+fn)
        docArr.append(tmp)
    return docArr

def getAllDrPhysician(cursor, cnx):
    query = ("SELECT username, fname, lname FROM doctorTable WHERE drType=%s")         #BETWEEN %s AND %s")
    cursor.execute(query, ("physician",)) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    docArr = []
    for un,fn,ln in cursor:
        tmp = str(un+" - "+ln+", "+fn)
        docArr.append(tmp)
    return docArr

def getAllDrLife(cursor, cnx):
    query = ("SELECT username, fname, lname FROM doctorTable WHERE drType=%s")         #BETWEEN %s AND %s")
    cursor.execute(query, ("lifecoach",)) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    docArr = []
    for un,fn,ln in cursor:
        tmp = str(un+" - "+ln+", "+fn)
        docArr.append(tmp)
    return docArr

def getNameFromUsername(username, cursor, cnx): 
    #the 2 queries need to have the same # of attributes in the select for a union
    query = ("SELECT fname, lname FROM doctorTable WHERE username = %s " ) #always check drTable 1st (smaller)
    cursor.execute(query, (username, ))
    for f, l in cursor:
        return str(f+" "+l)
    
    query = ("SELECT fname, lname FROM patientTable WHERE username = %s " ) #always check patTable 2nd (much larger)
    cursor.execute(query, (username,))
    for f, l in cursor:
        return str(f+" "+l)

    return "N/A N/A"

def getAllUnassignedPatients(cursor, cnx):
    query = ("SELECT username, creationDate FROM patientTable WHERE drOne = %s OR drTwo=%s OR drThree=%s" )
    cursor.execute(query, ("N/A","N/A","N/A"))
    unassigned = []
    for un, cd in cursor:
        unassigned.append(un)
    return unassigned

def getAcctFromUsername(username, cursor, cnx):
    query = ("SELECT username, fname, lname, email, creationDate FROM doctorTable WHERE username = %s")   
    cursor.execute(query, (username, ))
    for u, f, l, e, cD in cursor:
        return (u, "doctor",str(f+" "+l), e, cD)
    
    query = ("SELECT username, fname, lname, email, creationDate FROM patientTable WHERE username = %s")   
    cursor.execute(query, (username, ))
    for u, f, l, e, cD in cursor:
        return (u, "patient",str(f+" "+l), e, cD)
    return

def userAcctInfo(user, cursor, cnx):
    query = ("SELECT email, fname, lname, password FROM doctorTable WHERE username = %s")   
    cursor.execute(query, (user, ))
    for emailAdd,fn, ln,passw in cursor:
        return (emailAdd,fn, ln,passw)
    
    query = ("SELECT email, fname, lname, password FROM patientTable WHERE username = %s")   
    cursor.execute(query, (user, ))
    for emailAdd,fn, ln,passw in cursor:
        return (emailAdd,fn, ln,passw)
    return
    

def updateUserAcct(user, emailAdd,fn, ln,passw, cursor, cnx):
    if(passw==""): #if password is not being updated
        try:
            valid = validate_email(emailAdd)
        except:
            return "bad email or domain"
    
        if len(fn)<2 or len(ln)<2:
            return "short name error"
        
        result = getAcctFromUsername(user, cursor, cnx)
        if(result[1]=='doctor'):
            update_test = (
                "UPDATE doctorTable SET email=%s, fname=%s, lname=%s"
                "WHERE username = %s")
            cursor.execute(update_test, (emailAdd, fn, ln, user))
            cnx.commit()
            return "success"
        else:
            update_test = (
                "UPDATE patientTable SET email=%s, fname=%s, lname=%s"
                "WHERE username = %s")
            cursor.execute(update_test, (emailAdd, fn, ln, user))
            cnx.commit()
            return "success"
    else:
        
        policy = PasswordPolicy.from_names(
            length=8,  # min length: 8
            uppercase=1,  # need min. 2 uppercase letters
            numbers=1  # need min. 2 digits
            )
        isEnough = policy.test(passw)
        if len(isEnough)!=0:
            return "weak password"
        try:
            valid = validate_email(emailAdd)
        except:
            return "bad email or domain"

        if len(fn)<2 or len(ln)<2:
            return "short name error"

        result = getAcctFromUsername(user, cursor, cnx)
        if(result[1]=='doctor'):
            update_test = (
                "UPDATE doctorTable SET email=%s, fname=%s, lname=%s, password = %s "
                "WHERE username = %s")
            cursor.execute(update_test, (emailAdd, fn, ln, pwd_context.hash(passw), user))
            cnx.commit()
            return "success"
        else:
            update_test = (
                "UPDATE patientTable SET email=%s, fname=%s, lname=%s, password = %s "
                "WHERE username = %s")
            cursor.execute(update_test, (emailAdd, fn, ln, pwd_context.hash(passw), user))
            cnx.commit()
            return "success"


    
    
    

def deleteUserAcct(username, cursor, cnx):
    result = getAcctFromUsername(username, cursor, cnx)
    if(result[1]=='doctor'):
        delete_test = (
            "DELETE FROM doctorTable " #table name NOT db name
            "WHERE username = %s")
        cursor.execute(delete_test, (username,))
        cnx.commit()
    else:
        delete_test = (
            "DELETE FROM patientTable " #table name NOT db name
            "WHERE username = %s")
        cursor.execute(delete_test, (username,))
        cnx.commit()
    return "deleted "+username


def getAllApptsFromUsername(username, cursor, cnx):
    query = ("SELECT mtgID, mtgName, startTime FROM apptTable")         #BETWEEN %s AND %s")
    cursor.execute(query) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    patientArr = []
    for mI, mN, sT in cursor:
        patientArr.append([mI, mN, sT])
    return patientArr

def isMeetingIDValid(mtgid, cursor, cnx):
    query = ("SELECT mtgID FROM apptTable WHERE mtgID = %s")         #BETWEEN %s AND %s")
    cursor.execute(query, (mtgid, )) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    for item in cursor:
        return True
    return False

def getApptFromMtgId(mtgid, cursor, cnx):
    query = ("SELECT mtgID, doctor, patient, mtgName, startTime, joinURL FROM apptTable")         #BETWEEN %s AND %s")
    cursor.execute(query) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
    patientArr = []
    for mI, d, p, mN, sT, jU in cursor:
        return (mI, d, p, mN, sT, jU)

def createAppt(mtgName, mtgid, doctor, patient, start_time, joinURL, cursor, cnx):
    formatInsert = ("INSERT INTO apptTable "
                   "(mtgID, doctor,patient,mtgName,"
                    "startTime,joinURL) "
                   "VALUES (%s, %s,%s, %s,%s, %s)") #NOTE: use %s even with numbers
    insertContent = (mtgid, doctor, patient, mtgName, start_time, joinURL)
    cursor.execute(formatInsert, insertContent)
    cnx.commit()
    return "success create"

def deleteAppt(mtgid, cursor, cnx):
    delete_test = (
        "DELETE FROM apptTable " #table name NOT db name
        "WHERE mtgID = %s")
    cursor.execute(delete_test, (mtgid,))
    cnx.commit()
    # for item in cursor:
    #     return "deleted "+mtgid
    

def updateAppt(mtgName, mtgid,start_time, cursor, cnx): 
    update_test = (
                "UPDATE apptTable SET mtgName=%s, startTime=%s "
                "WHERE mtgID = %s")
    cursor.execute(update_test, (mtgName,start_time, mtgid))
    cnx.commit()
    return "success update"

# query = ("SELECT * FROM apptTable ")         #BETWEEN %s AND %s")
# cursor.execute(query) #NOTE: even if there is only 1 condition, you have to make the item passed to the query into a TUPLE
# for item in cursor:
#    print(item) #each item = a row = a tuple




cursor.close()
cnx.close()