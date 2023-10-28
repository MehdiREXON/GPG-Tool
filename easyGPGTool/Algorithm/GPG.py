import gnupg, os
from colorama import Fore
from sys import platform


class newGPG(gnupg.GPG):
    def __init__(
        self,
        gpgbinary="gpg",
        gnupghome=None,
        verbose=False,
        use_agent=True,
        keyring=None,
        options=None,
        secret_keyring=None,
        env=None,
    ):
        if platform == "darwin":  # MacOS
            gnupghome = "/Users/" + os.getenv("USER") + "/.gnupg"
        elif platform == "linux" or platform == "linux2":  # Linux
            gnupghome = "/home/" + os.getenv("USER") + "/.gnupg"
        super().__init__(
            gpgbinary,
            gnupghome,
            verbose,
            use_agent,
            keyring,
            options,
            secret_keyring,
            env,
        )
        self.encoding = "utf-8"

    def getKeys(self, private: bool = False) -> list[dict]:
        if private:
            return self.list_keys()
        else:
            return self.list_keys(secret=True)

    def generateKey(self, **kwargs) -> bytes:
        inputData = self.gen_key_input(
            key_type=kwargs.get("key_type", "RSA"),
            key_length=kwargs.get("key_length", 1024),
            name_real=kwargs.get("fullname", "Autogenerated Key"),
            name_comment=kwargs.get("comment", "Generated by easyGPG Tool"),
            name_email=kwargs.get("email", ""),
            passphrase=kwargs.get("passphrase", ""),
            expire_date=kwargs.get("expireDate", 0),  # 0 means lifetime
        )
        key = self.gen_key(inputData)

        if not key or key == "":
            raise RuntimeError("Failed to generate key")

        return key

    def removeKey(self, **kwargs) -> tuple(bool,str):
        ## Removing Private Key First
        result = self.delete_keys(
            fingerprints=kwargs.get("fingerprint", ""),
            passphrase=kwargs.get("passphrase", ""),
            secret=True,
        )
        if result.status != 'ok':
            return (False,result.stderr)
        
        result = self.delete_keys(
            fingerprints=kwargs.get("fingerprint", "")
        )

        if result.status !='ok':
            return (False,result.stderr)
        
        else: 
            return(True,'')
        
        
    ## Will be introduced in 0.3
    # def encrypt(self, data, recipients, **kwargs) -> tuple(bool,str,str):
    #     if self.list_keys(False) == [] and self.list_keys(True) == []:
    #         raise RuntimeError("No such key to encrypt")
        
    #     status = self.encrypt(data=data,recipients=recipients,armor= kwargs.get('armor',True),output = kwargs.get('output'))
        
    #     if status.ok:
    #         return (True,status.status,status.data)
        
    
class easyGPG:
    def __init__(self):
        super().__init__()
        os.environ["GPG_AGENT_INFO"] = ""
        if platform == "darwin":  # MacOS
            self.gpg = gnupg.GPG(gnupghome="/Users/" + os.getenv("USER") + "/.gnupg")
        elif platform == "linux" or platform == "linux2":  # Linux
            self.gpg = gnupg.GPG(gnupghome="/home/" + os.getenv("USER") + "/.gnupg")
        self.gpg.encoding = "utf-8"

    def getKeys(self, secret: bool = False):
        if secret:
            return self.gpg.list_keys(secret=True)
        else:
            return self.gpg.list_keys(secret=False)

    def generate_key(self, data):
        inputData = self.gpg.gen_key_input(
            name_email=data["email"],
            passphrase=data["passphrase"],
            key_type=data["key_type"],
            key_length=data["key_length"],
            name_real=data["fullname"],
        )
        easyGPG.key = str(self.gpg.gen_key(inputData))
        if easyGPG.key == "":
            self.sendLog("the app couldn't create a key", Fore.RED)
            raise Exception("the app couldn't create a key")
        else:
            self.sendLog(
                "a key created with this fingerprint : " + easyGPG.key, Fore.GREEN
            )

    def removeKey(self, mainWindow, state):
        if state:
            result = self.gpg.delete_keys(
                mainWindow.removeKeyForm.fingerprintLineEdit.text(),
                passphrase=mainWindow.removeKeyForm.passphraseLineEdit.text(),
                secret=True,
            )
            if result.status == "ok":
                easyGPG.key = ""
                return result
            else:
                self.sendLog(result.stderr, Fore.RED)
                raise Exception(result.stderr)
        else:
            result = self.gpg.delete_keys(
                mainWindow.removeKeyForm.fingerprintLineEdit.text()
            )
            if result.status == "ok":
                easyGPG.key = ""
                return result
            else:
                self.sendLog(result.stderr, Fore.RED)
                raise Exception(result.stderr)

    def encrypt(self, email):
        from PySide6.QtWidgets import QFileDialog

        permission = False
        if self.gpg.list_keys(False) == [] and self.gpg.list_keys(True) == []:
            raise Exception("No such key")
        for this in self.gpg.list_keys(True):
            a = this["uids"][0].split("<")[1].replace(">", "")
            if this["uids"][0].split("<")[1].replace(">", "") == email:
                permission = True
                break
        if permission is not True:
            raise Exception("No such key")
        else:
            selectedFile = QFileDialog.getOpenFileName(
                self, "select your file", "/home/" + os.getlogin() + "/Desktop"
            )
            if not self.encryptForm.signCB.isChecked():
                with open(os.path.abspath(selectedFile[0]), "rb") as file:
                    status = self.gpg.encrypt_file(
                        file,
                        recipients=email,
                        output=os.path.splitext(selectedFile[0])[0] + ".safe",
                    )
            else:
                with open(os.path.abspath(selectedFile[0]), "rb") as file:
                    status = self.gpg.encrypt_file(
                        file,
                        recipients=email,
                        output=os.path.splitext(selectedFile[0])[0] + ".safe",
                        sign=self.encryptForm.fingerprintLineEdit.text(),
                        passphrase=self.encryptForm.passphraseLineEdit.text(),
                    )
        return status

    def decrypt(self, passphrase):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from easyGPGTool.GUI._extensions_ import Ext
        import magic

        fileExtension = "log"

        selectedFile = QFileDialog.getOpenFileName(
            self,
            "select your decrypted file",
            "/home/" + os.getlogin() + "/Desktop",
            filter="*.safe",
        )
        try:
            if selectedFile == "":
                raise Exception("path is empty")
            with open(str(selectedFile[0]), "rb") as file:
                status = self.gpg.decrypt_file(
                    file,
                    passphrase=passphrase,
                    output=os.path.splitext(selectedFile[0])[0],
                )

            with open(os.path.splitext(selectedFile[0])[0], "rb") as file:
                tmpExtFile = magic.from_file(
                    os.path.splitext(selectedFile[0])[0], mime=True
                )

            for ext in Ext.data.keys():
                if Ext.data[ext]["mime"] == tmpExtFile:
                    fileExtension = ext
                    break

            os.rename(
                os.path.splitext(selectedFile[0])[0],
                os.path.splitext(selectedFile[0])[0] + "." + fileExtension,
            )

            return status
        except Exception as ex:
            QMessageBox.critical(self, "decrypting a file", str(ex), QMessageBox.Ok)

    def exportKey(self, status, armor):
        from PySide6.QtWidgets import QFileDialog

        if not status:
            pubKey = self.gpg.export_keys(
                self.exportForm.emailLineEdit.text(), armor=armor
            )
            if pubKey == "":
                raise Exception("no such key(invalid ID)")

            selectedPath = QFileDialog.getExistingDirectory(
                self, "select your file", "/home/" + os.getlogin() + "/Desktop"
            )

            if selectedPath == "":
                raise Exception("empty path can not be used")

            if armor:
                with open(selectedPath + "/pubKey.asc", "w") as file:
                    file.write(pubKey)
            else:
                with open(selectedPath + "/pubKey", "wb") as file:
                    file.write(pubKey)

            return (selectedPath, False)
        else:
            privateKey = self.gpg.export_keys(
                self.exportForm.emailLineEdit.text(),
                True,
                passphrase=self.exportForm.passphraseLineEdit.text(),
                armor=armor,
            )
            if privateKey == "":
                raise Exception("id is not valid")

            selectedPath = QFileDialog.getExistingDirectory(
                self, "select your file", "/home/" + os.getlogin() + "/Desktop"
            )

            if selectedPath == "":
                raise Exception("empty path can not be used")

            if armor:
                with open(selectedPath + "/privateKey.asc", "w") as file:
                    file.write(privateKey)
            else:
                with open(selectedPath + "/privateKey", "wb") as file:
                    file.write(privateKey)

            return (selectedPath, True)

    def importKey(self, status):
        if not status:
            result = self.gpg.import_keys_file(self.importForm.keyPathLineEdit.text())
            if result.returncode == 0:
                return (result.stderr, False)
            else:
                raise Exception(result.stderr)
        else:
            result = self.gpg.import_keys_file(
                self.importForm.keyPathLineEdit.text(),
                passphrase=self.importForm.passphraseLineEdit.text(),
            )
            if result.returncode == 0:
                return (result.stderr, True)
            else:
                raise Exception(result.stderr)

    def sendLog(self, txt_or_exception, status):
        from datetime import datetime

        print(f"{status}[LOG]", datetime.now(), txt_or_exception, f" {Fore.RESET}")

    def changeTrust(self, mainWindow, mode):
        result = self.gpg.trust_keys(
            mainWindow.trustForm.fingerprintCB.currentText(), mode
        )
        if result.status != "ok":
            raise Exception(result.stderr)
        return result
