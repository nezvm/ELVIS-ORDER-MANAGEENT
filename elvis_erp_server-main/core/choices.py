import calendar
import datetime
from datetime import date

BOOL_CHOICES = (("", "---------------"), (True, "Yes"), (False, "No"))

COLLECTION_MODE_CHOICES = (("CASH", "Cash"), ("CHEQUE", "Cheque"), ("BANK_TRANSFER", "Bank Transfer"), ("OTHERS", "Others"))

ATTENDANCE_LOCATION_CHOICES = (("HOME", "HOME"), ("OFFICE", "OFFICE"))

CONTACT_TYPE_CHOICES = (("PHONE", "PHONE"), ("WHATSAPP", "WHATSAPP"), ("EMAIL", "EMAIL"), ("SMS", "SMS"))

EXPERIENCE_CHOICES = (("EXPERIENCED", "Experienced"), ("FRESHER", "Fresher"))

EMPLOYMENT_TYPE_CHOICES = (("PERMANENT", "Permanent"), ("PROBATION", "Probation"), ("CONTRACT", "Contract"), ("TEMPORARY", "Temporary"))

EDUCATION_TYPE_CHOICES = (("PROFESSIONAL", "Professional"), ("VOCATIONAL", "Vocational"), ("OTHERS", "Others"))

GENDER_CHOICES = (("", "----------------"), ("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other"), ("NOT_SPECIFIED", "Not Specified"))

GST_CHOICES = (("unregistered", "Unregistered/Consumer"), ("regular", "Registered - Regular"), ("composite", "Registered -Composite"))

JOB_TYPE_CHOICES = (("Contructual", "Contructual"), ("Permanent", "Permanent"), ("Probation", "Probation"))

ORIGIN_CHOICES = (("UAE", "UAE"), ("Qatar", "Qatar"), ("Oman", "Oman"), ("Kuwait", "Kuwait"), ("KSA", "KSA"), ("EXPAT", "EXPAT"), ("Bahrain", "Bahrain"))

PAYMODE_CHOICES = (("CASH", "Cash on Hand"), ("BANK", "Bank Account"), ("WPS", "WPS - Wages Protection System"))

PRIORITY_CHOICES = (("Urgent", "Urgent"), ("High", "High"), ("Medium", "Medium"), ("Low", "Low"))

READINESS_CHOICES = (("3", "Within 3 Months"), ("5", "with 1 year"), ("6", "Within 6 Months"), ("12", "Within 12 Months"))

RELATION_CHOICES = (("Child", "Child"), ("Father", "Father"), ("Husband", "Husband"), ("Mother", "Mother"), ("Spouse", "Spouse"), ("Wife", "Wife"))

REQUEST_STATUS_CHOICES = (("AWAITING", "Awaiting"), ("ACCEPTED", "Accepted"), ("rejected", "Rejected"), ("COMPLETED", "Completed"))

RETIRE_TYPE_CHOICES = (("None", "None"), ("NOR", "Normal"), ("REG", "Resignation"), ("TER", "Termination"), ("VRS", "VRS"))

RATING_CHOICES = ((1, "One"), (2, "Two"), (3, "Three"), (4, "Four"), (5, "Five"))

STATUS_CHOICES = (("on_hold", "On hold"), ("rejected", "Rejected"), ("approved", "Approved"))

SALUTATION_CHOICES = (("Dr.", "Dr."), ("Miss", "Miss"), ("Mr", "Mr"), ("Mrs", "Mrs"), ("Prof.", "Prof."))

TAX_CHOICES = ((0, "0 %"), (5, "5 %"), (10, "10 %"), (12, "12 %"), (15, "15 %"), (18, "18 %"), (20, "20 %"))

YEAR_CHOICES = [(str(y), y) for y in range(2022, datetime.date.today().year + 3)]

MONTH_CHOICES = [(str(i), calendar.month_name[i]) for i in range(1, 13)]

TAG_CHOICES = (("primary", "Blue"), ("secondary", "Orange"), ("success", "Green"), ("warning", "Yellow"), ("danger", "Red"))


BLOOD_CHOICES = (
    ("a-positive", "A +Ve"),
    ("b-positive", "B +Ve"),
    ("ab-positive", "AB +Ve"),
    ("o-positive", "O +Ve"),
    ("a-negative", "A -Ve"),
    ("b-negative", "B -Ve"),
    ("ab-negative", "AB -Ve"),
    ("o-negative", "O -Ve"),
)

COLOR_PALETTE = [
    ("#FF5733", "#FF5733"),
    ("#FFBD33", "#FFBD33"),
    ("#DBFF33", "#DBFF33"),
    ("#75FF33", "#75FF33"),
    ("#33FF57", "#33FF57"),
    ("#33FFBD", "#33FFBD"),
    ("#FF58DE", "#FF58DE"),
    ("#7C80FF", "#7C80FF"),
]


