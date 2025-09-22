from iqoptionapi.stable_api import IQ_Option
error_password="""{"code":"invalid_credentials","message":"You entered the wrong credentials. Please check that the login/password is correct."}"""
iqoption = IQ_Option("anaveleci@gmail.com", "carlasebas23", 1)
check,reason=iqoption.connect()
if check:
    print("Activa tu robot")
    #Si ves esto puedess cerrar la conexión para probarlo
    while True:
        if iqoption.check_connect()==False:#Detecta si el websocket ha sido cerrado
            print("Probando a reconectar")
            check,reason=iqoption.connect()
            if check:
                print("Reconectado con éxito")
            else:
                if reason==error_password:
                    print("Contraseña incorrecta")
                else:
                    print("No hay conexión")

else:

    if reason=="[Errno -2] Nombre or servicio no conocido":
        print("No hay conexión")
    elif reason==error_password:
        print("Error en la Contraseña")
