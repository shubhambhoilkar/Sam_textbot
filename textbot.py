from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import requests
import json
from datetime import datetime, time

api_key = "YOUR_OPENAI_API_KEY"
client = OpenAI(api_key=api_key)

session_store = {}

API_URL = "https://stgbot.genieus4u.ai/api/cb"
CLIENT_APP_KEY = "44ihRG38UX24DKeFzE15FbbPZfCgz3rh"

datetime_= None


def fetch_dates():
    payload = {
        "route": "appointment_info",
        "client_app_key": CLIENT_APP_KEY
    }
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        formatted = {item['date']: item['slots'] for item in data.get("available_dates", []) if item['slots']}
        dates = list(formatted.keys())
        return dates
    except Exception as e:
        print("Failed to fetch dates:", e)
        return {}

def fetch_periods(date):
    payload = {
        "route": "appointment_info",
        "client_app_key": CLIENT_APP_KEY
    }
    try:
        response = requests.post(API_URL, json = payload)
        response.raise_for_status()
        data=response.json()
        formatted = {item['date']: item['slots'] for item in data.get("available_dates", []) if item['slots']}
        slots=formatted[date]
        morning, afternoon, evening, output=[], [], [], []
        for slot in slots:
            slot24 = datetime.strptime(slot, "%I:%M %p").time()
            if (time(0,0) <= slot24) and (slot24<=time(11,59)):
                morning.append(slot)
            elif (time(12,0) <= slot24) and (slot24<=time(17,59)):
                afternoon.append(slot)
            elif (time(18,0) <= slot24) and (slot24<=time(23,59)):
                evening.append(slot)
        output = []
        if morning: output.append("Morning")
        if afternoon: output.append("Afternoon")
        if evening: output.append("Evening")
        return output
    except Exception as e:
        print("Failed to fetch time periods:", e)
        return {}

def fetch_timeslots(date, period):
    payload = {
        "route": "appointment_info",
        "client_app_key": CLIENT_APP_KEY
    }
    time_period_mapper={"morning":[(0,0),(11,59)],"afternoon":[(12,0),(17,59)],"evening":[(18,0),(23,59)]}
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        formatted = {item['date']: item['slots'] for item in data.get("available_dates", []) if item['slots']}
        slots=formatted[date]
        t1,t2=time_period_mapper[period.lower()][0],time_period_mapper[period.lower()][1]
        time1=time(t1[0],t1[1])
        time2=time(t2[0],t2[1])

        output=[]
        if slots:
            for slot in slots:
                slot24 = datetime.strptime(slot, "%I:%M %p").time()
                if  (slot24 <=time2) and (slot24 >= time1):
                    output.append(slot)
            return output

    except Exception as e:
        print("Failed to fetch slots:", e)
        return {}
    
def book_appointment(user_data):
    try:
        headers = {
            "Content-type":"application/json"
        }
        payload ={
            "route": "process_data",
            "content_type": "appointment_confirmation",
            "client_id": CLIENT_APP_KEY,
            "appointment_name": user_data["name"],
            "appointment_period": user_data["period"],
            "appointment_time": user_data["time_slot"],
            "appointment_date": user_data["date"],
            "appointment_email": user_data["email"],
            "appointment_phone_number": user_data["phone"],
            "appointment_country_id": "en",
            "user_timezone": ""
        }
        response = requests.post(API_URL, headers = headers, json = payload)
        if response.status_code == 200:
            return {
                "response": "Appointment Confirmed Sam!!" 
        }
        else: 
            return {
                "response":"OOPS something wrong Sam."
            }
    except Exception as e:
        return False , f" Booking appointment failed with status: {response.status_code} and {response.text}"

def Cancel_appointment(user_data):   #user_data
    try:
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "client_id" : CLIENT_APP_KEY,
            "route": "cancel_appointment",
            "user_id" : user_data.get("user_id",""),
            "appointment_date":user_data["date"],
            #"appointment_period":"period",
            "appointment_time": user_data["time_slot"]
        }
        response = requests.post(url = API_URL, headers= headers, json = payload)
        print("📤 Cancel API response:", response.status_code, response.text)
        
        if response.status_code == 200:
            return True , "✅ Appointment cancelled successfully."
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def validate_required(data, required):
    return [field for field in required if not data.get(field)]


def request_call(user_data):
    try:
        headers= {
            "Content-Type": "applicaton/json"
        }
        payload = {
            "client_id":"44ihRG38UX24DKeFzE15FbbPZfCgz3rh",
            "user_timezone":"Asia/Kolkata",
            "callback_name": user_data["name"],
            "callback_phone": user_data["phone"],
            "callback_region": user_data["region"],
            "route":"process_callback_data"
        }
        response = requests.post(url=API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return True, "✅ Your Call request is Confirmed. Our team will call you accordingly."
        else:
            return False, f"❌ Unable to book a call request. Please try once again {request_call}"
    except Exception as e:
        return False, str(e)


system_prompt = {
    "role": "system",
    "content": (
        """
        **PERSONA:**
        You are a smart and friendly AI customer support assistant for a service company.
        You assist users with fetching available slots for booking appointments .
        For this you work exact according to the tool calling function only.
        You receive a structured payload with information such as `user_id`, `text`.

        **GENERAL BEHAVIOR:**
        - Always be polite and guide users step-by-step.
        - Ask clarifying questions only when information is missing or ambiguous.
        - Normalize loosely formatted times like "9", "9am", "10.30am" to standard 12-hour format (e.g., '9:00 AM').

        **APPOINTMENT BOOKING WORKFLOW:**
        1. If user wants to book an appointment, use tool 'get_available_slots' to display appointment dates on user's screen and say some thing like 'Please select a suitable date for appointment'.
        2. When a user selects a valid date, call tool 'fetch_periods' with parameter 'date' = user selected date in yyyy-mm-dd format. This will display available time periods (Morning, Afternoon, Evening) for given date on user's screen.
        3. When a user selects a valid time period, call tool 'fetch_timeslots' and here push the date and time_periods that was selected by user.
        4. Finally call `book_appointment` tool function by passing all this data of selected Date, time_periods and time_slots to  and ask for the Full name, Email and phone. 

        **APPOINTMENT CANCELLATION WORKFLOW:**
        1. If a user wants to cancel an appointment:
            - Ask for the appointment `date` (YYYY-MM-DD) and exact `time`.
            - Confirm the details with the user.
            - Call `Cancel_appointment`.

        **GENERAL RULES:**
        - Use all available information from the payload before asking the user anything.
        - Be helpful, step-by-step, and friendly at all times.
        - If user input is vague, ask clarifying questions.
        - If user asks something out of scope, politely say you only help with appointment-related services.
        """
    )
}
def run_conversation(user_input):
    user_id = session_id = user_input["user_id"]
    state = session_store.setdefault(session_id, {
        "messages": [system_prompt],
        "user_data": {}
    })

    memory = state["messages"]
    memory.append({"role": "user", "content": user_input["text"]})

    tools = [
        {
            "type": "function",
            "function": {
                "name": "fetch_dates",
                "description": "Fetch available dates for appointments.",
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_periods",
                "description": "Fetch available time periods (Morning, Afternoon, Evening) for given date (yyyy-mm-dd format).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "appointment date selected by the user"}
                    },
                    "required": ["date"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_timeslots",
                "description": "Fetch available timeslots for given date (yyyy-mm-dd format) and time period.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string", 
                            "description": "appointment date selected by the user"},
                        "period":{
                            "type": "string",
                            "enum" : ["Morning", "Afternoon", "Evening"],
                            "description": "appointment period selected by the user."
                        }
                    },
                    
                "required": ["date","period"],
            }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Used to store and confirm the appointment details to the database for appointment booking purpose",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type":"string", "description": "Full name given by the user"},
                        "email": {"type": "string", "description": "email ID by the user"},
                        "phone": {"type": "string", "description": "phone number by the user"},
                        "date": {"type": "string", "description": "appointment date selected by the user"},
                        "period": {"type": "string", "description": "appointment time period (Morning, Afternoon, Evening) selected by the user"},
                        "time_slot":{"type" :"string", "description": "appointment time slot selected by the user"} 
                    },
                    "required": ["name","email","phone","date","period","time_slot"],
                }
            }
        },
        {
            "type":"function",
            "function":{
            "name": "Cancel_appointment",
            "description": "Cancelling the pre booked appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "appointment_date": {"type": "string"},
                    "appointment_time": {"type": "string"}
                },
                "required": ["appointment_date", "appointment_time"]
                }
            }
        },
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=memory,
        user=user_id,
        tools=tools,
    )
    #msg = response["choices"][0]["message"]
    message = response.choices[0].message

    if getattr(message, "tool_calls", None):
        tool_call = message.tool_calls[0]
        memory.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": getattr(message, "tool_calls", None)
        })

        if tool_call.function.name == "fetch_dates":
            slots = fetch_dates()

            memory.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(slots),
            })

            followup = client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                messages=memory,
                user=user_id
            )
            final_message = followup.choices[0].message
            memory.append({"role": "assistant", "content": final_message.content})
            return {
                "response": "Please select a suitable date for the appointment.",
                "buttons": slots,
                "messages": memory
            }

        if tool_call.function.name == "fetch_periods":
            args_str = tool_call.function.arguments
            args = json.loads(args_str)
            periods = fetch_periods(args["date"])

            memory.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(periods),
            })

            followup = client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                messages=memory,
                user=user_id
            )
            final_message = followup.choices[0].message 

            return {
                "response": f"Great choice! The available time periods for {args['date']} are:",
                "buttons": periods,
                "messages": memory
            }



        if tool_call.function.name == "fetch_timeslots":
            args_str = tool_call.function.arguments
            args=json.loads(args_str)
            slots = fetch_timeslots(args["date"], args["period"])

            memory.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(slots)
            })

            followup = client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                messages=memory,
                user=user_id
            )
            final_message = followup.choices[0].message

            return {
                "response": f"Here are the available {args['period']} slots for {args['date']}:",
                "buttons": slots,
                "messages": memory
            }

        if tool_call.function.name == "book_appointment":
            args_str = tool_call.function.arguments
            args = json.loads(args_str)

            # merge into session state
            state["user_data"].update(args)
            user_data = state["user_data"]

            required_fields = ["name", "email", "phone", "date", "period", "time_slot"]
            missing = [f for f in required_fields if f not in user_data or not user_data[f]]

            if missing:
                next_field = missing[0]
                if next_field == "name":
                    response_text = "May I have your full name please?!"
                elif next_field == "email":
                    response_text = "Could you please provide your email ID?!"
                elif next_field == "phone":
                    response_text = "Kindly provide your phone number"
                else:
                    response_text = f"Please provide {next_field}"

                return {
                    "response": response_text,
                    "buttons": [],
                    "messages": memory
                }

            # ✅ all fields present → book
            print("Check user_data: ", user_data)
            details = book_appointment(user_data)

            memory.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(details)
            })

            return {
                "response": f"✅ Appointment booked successfully for {user_data['date']} "
                            f"({user_data['period']} - {user_data['time_slot']}). "
                            f"Confirmation sent to {user_data['email']}.",
                "buttons": [],
                "messages": memory
            }
        
        if tool_call.function.name == "Cancel_appointment":
            args_str = tool_call.function.arguments
            args = json.loads(args_str)

            # normalize keys
            if "time" in args and "time_slot" not in args:
                args["time_slot"] = args["time"]
            if "appointment_date" in args and "date" not in args:
                args["date"] = args["appointment_date"]
            if "appointment_time" in args and "time_slot" not in args:
                args["time_slot"] = args["appointment_time"]

            # merge into session state
            state["user_data"].update(args)
            user_data = state["user_data"]

            required_fields = ["date", "time_slot"]
            missing = [f for f in required_fields if f not in user_data or not user_data[f]]

            if missing:
                # ask for the next missing field
                if "date" in missing:
                    response_text = "Please provide the date of the appointment you want to cancel (YYYY-MM-DD)."
                else:
                    response_text = "Please provide the exact time of the appointment you want to cancel."

                # 🔑 always append a tool response (stub)
                memory.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"success": False, "message": f"Missing {', '.join(missing)}"})
                })

                return {
                    "response": response_text,
                    "buttons": [],
                    "messages": memory
                }

            # ✅ Safe to cancel appointment
            success, result = Cancel_appointment(user_data)

            memory.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"success": success, "message": result})
            })

            return {
                "response": f"✅ Appointment on {user_data['date']} at {user_data['time_slot']} has been cancelled.",
                "buttons": [],
                "messages": memory
            }
        
        if tool_call.function.name == "request_call":
            args_str = tool_call.function.arguments
            args = json.loads(args_str)

    return {
        "response": (message.content or "" ).strip(),
        "buttons": [],
        "messages":memory
    }

#Back up:
while True:
    text_input = input("Enter your message: ")
    user_input = {"user_id": "99", "text": text_input}
    if text_input:
        data = run_conversation(user_input)
        print("Bot:", data["response"])
        if data["buttons"]:
            print("Options:", data["buttons"])