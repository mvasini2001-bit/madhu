import bcrypt

password =input( "Enter password" )
hashed_password = bcrypt.hashpw(
    password.encode("utf-8"),
    bcrypt.gensalt()
)
print("Password hash:")
print(hashed_password.decode("utf-8"))    
