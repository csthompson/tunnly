package main

import (
  "crypto/aes"
  "crypto/cipher"
  "encoding/base64"
  "io/ioutil"

  "fmt"
  "io"
  "net/http"
  "bytes"
  _"flag"
  "code.google.com/p/gopass"
  "errors"
  "strings"
  "os/exec"
  "os"
  "log"
)

//Decrypt file
func decrypt2(key, text []byte) ([]byte, error) {
  block, err := aes.NewCipher(key)
  if err != nil {
    return nil, err
  }
  if len(text) < aes.BlockSize {
    return nil, errors.New("ciphertext too short")
  }
  iv := text[:aes.BlockSize]
  text = text[aes.BlockSize:]
  cfb := cipher.NewCFBDecrypter(block, iv)
  cfb.XORKeyStream(text, text)
  data, err := base64.StdEncoding.DecodeString(string(text))
  if err != nil {
    return nil, err
  }
  return data, nil
}

func decrypt(key, text []byte) ([]byte, error) {
  
  ciphertext, _ := base64.StdEncoding.DecodeString(string(text))
  //ciphertext := text

  //fmt.Println(len(ciphertext))

  block, err := aes.NewCipher(key)
  if err != nil {
    panic(err)
  }

  // The IV needs to be unique, but not secure. Therefore it's common to
  // include it at the beginning of the ciphertext.
  if len(ciphertext) < aes.BlockSize {
    panic("ciphertext too short")
  }
  iv := ciphertext[:16]

  // CBC mode always works in whole blocks.
  if len(ciphertext)%aes.BlockSize != 0 {
    fmt.Println(len(ciphertext)%aes.BlockSize)
    panic("ciphertext is not a multiple of the block size")
  }

  ciphertext = ciphertext[aes.BlockSize:]

  mode := cipher.NewCBCDecrypter(block, iv)

  // CryptBlocks can work in-place if the two arguments are the same.
  mode.CryptBlocks(ciphertext, ciphertext)

  //fmt.Println(string(ciphertext))

  //Unpad the ciphertext
  pad := int(ciphertext[len(ciphertext)-1])
  ciphertext = ciphertext[:len(ciphertext)-pad]

  return ciphertext, nil
}

//Decrypt the OVPN bytes and write to file
func writeFile(_content []byte, _passphrase string, _filename string) {

  data := _content

  clearText, err := decrypt([]byte(_passphrase + "0000000000000000000000000000"), data)
  if err != nil {
    fmt.Println(err)
  }

  ioutil.WriteFile(_filename,clearText,0644)

}

//Helper function to download the client and copy to byte array
func downloadFromUrl(url string) []byte {

  buf := bytes.NewBuffer(nil)

  fmt.Println(url)

  response, err := http.Get(url)
  if err != nil {
    fmt.Println("Error while downloading", url, "-", err)
    return []byte{}
  }
  defer response.Body.Close()

  n, err := io.Copy(buf, response.Body)
  if err != nil {
    fmt.Println("Error while downloading", url, "-", err)
    return []byte{}
  }

  fmt.Println(n, "bytes downloaded...")
  fmt.Println("Connection parameters downloaded...")

  return buf.Bytes()
}

//Use the openvpn command line to connect to the network
func connect(filename string) {
  cmd := exec.Command("sudo", "/usr/local/sbin/openvpn", "--config", filename)
  result, _ := cmd.Output()
  fmt.Println(string(result))
}


func main() {

  args := os.Args[1:]

  if len(args) < 2 {
    log.Fatal("Tunnly requires 2 arguments!")
  }

  if args[0] == "connect" {
    data := downloadFromUrl("http://tunnly.opendev.io:5000/network/config/" + strings.TrimSpace(args[1]))

    pass, _ := gopass.GetPass("Please enter the passphrase:")

    writeFile(data, pass, args[1] + ".ovpn")

    connect(args[1] + ".ovpn")
  }

}
