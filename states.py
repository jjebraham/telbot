# states.py
from aiogram.fsm.state import State, StatesGroup

class RegisterState(StatesGroup):
    first_name = State()         # 1/9
    last_name = State()          # 2/9
    phone_number = State()       # 3/9
    national_id = State()        # 4/9
    dob = State()                # 5/9
    bank_card_number = State()   # 6/9
    terms = State()              # 7/9  (rules & conditions acceptance)
    front_id = State()           # 8/9
    back_id = State()            # 9/9

class RegistrationReview(StatesGroup):
    waiting = State()
    edit_nid = State()
    edit_dob = State()
    edit_card = State()

class LoginState(StatesGroup):
    phone = State()

class BankCardState(StatesGroup):
    adding = State()

class PaymentState(StatesGroup):
    website = State()
    site_account = State()
    site_password = State()
    amount = State()
    details = State()

