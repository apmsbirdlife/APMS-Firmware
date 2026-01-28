// APMS System Monitor V1.0 December 2023
// APMS System Monitor V1.1 January 2026
// Developed by Pierre Retief
// EEPROM: [0-12] holds mobile number of administrator

#include <EEPROM.h>
#include <SoftwareSerial.h>
#include <EEPROM.h>

#define pin_temp            A0
#define pin_4V              A6
#define pin_12V             A5
#define pin_5V              A3
#define pin_24V             A7

#define pin_rpi_shutdown    9
#define pin_led             13
#define pin_button          12
#define pin_buzzer          8

#define serial_sim_tx       3
#define serial_sim_rx       5

SoftwareSerial Serial_SIM800L(serial_sim_rx, serial_sim_tx); 

///////////////////////////////////////////////////////////////////////////////
// Global Variables
char boot_time_formatted[]      = "YYYY-MM-DD HH:MM:SS"; 
char date_time_formatted[]      = "YYYY-MM-DD HH:MM:SS";
char rpi_boot_time_formatted[]  = "YYYY-MM-DD HH:MM:SS";
int sms_on = 1;
int rpi_command_flag = 0;
char rpi_command[100] = {0};

size_t rpi_message_size = 0;

unsigned long timer_start_ms = 0;
unsigned long timer_val = 3; // number of seconds for timer, default 3
int rpi_flag = 1; // rpi on
char rpi_status[200] = {0};

float float_temperature = 0.0;
float float_4V  = 0.0;
float float_5V  = 0.0;
float float_12V = 0.0;
float float_24V = 0.0;

char mobile_number[13] = {0};
char old_mobile_number[13] = {0};


///////////////////////////////////////////////////////////////////////////////
// Function Prototypes
void get_mobile_number (void);
void program_new_mobile_number(const char* number);
int setup_SIM800L (void);
void clear_SIM800L_buffer (void);
void update_date_time (void);
void get_temperature (void);
void check_temperature (void);
void get_voltages (void);
void check_voltages (void);
void check_button (void);
void check_rpi (void);
void read_pi (char rpi_message[200]);
void pi_cmd_R (void);
void pi_cmd_S (void);
void pi_cmd_Q (void);
void pi_cmd_L (void);
void pi_cmd_P (void);

void clear_Serial1_buffer();

void print_rpi_status_report (void);
void start_timer(unsigned long sec);
int check_timer (void);
void send_status_report (void);
void check_sms (void);
void sms_alert (char* sms_alert_message);
void cmd_R();
void cmd_U(char* response);
void cmd_S();
void cmd_P();
void cmd_M (char* response);
void cmd_C (char* response);
void sms_status_report (void);
void sms (char* sms_message);
void rpi_power_on_off (void);
void led_on (void);
void led_off (void);
void beep (int num);

///////////////////////////////////////////////////////////////////////////////
void setup (void)
{
  Serial_SIM800L.begin(9600);
  Serial.begin(115200);
  Serial1.begin(115200);
  Serial1.setTimeout(10000);
  
  pinMode(pin_rpi_shutdown, OUTPUT);
  digitalWrite(pin_rpi_shutdown,  HIGH);
  
  pinMode(pin_led,          OUTPUT);
  pinMode(pin_buzzer,       OUTPUT);
  pinMode(pin_button,       INPUT_PULLUP);
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void loop (void)
{ 
  Serial.print("Starting Monitor...");
  delay(20000); // 20 sec delay to give device chance to connect to the mobile network
  beep(1);
  
  //Serial.println("Checking communication with SIM800L module...");
  
  //program_new_mobile_number("+27[PUT NUMBER HERE]");
  get_mobile_number();

  setup_SIM800L();
  sms("The APMS Monitor just booted...");
  
  // Serial1.print("Updating date/time...\t");
  update_date_time();

  // Serial1.print("date_time_formatted");
  // Serial1.print(date_time_formatted);

  strcpy(boot_time_formatted, date_time_formatted);

  Serial.println("Checking temperature...");
  
  get_temperature();
  check_temperature();
  
  get_voltages();
  check_voltages();
  check_button();
  check_rpi();
  check_sms();
 
  while(1)
  {
    get_temperature();
    
    ///////////////////////////////////////////////////////////////////////////////
    check_temperature();
    ///////////////////////////////////////////////////////////////////////////////


    get_voltages();
    ///////////////////////////////////////////////////////////////////////////////
    check_voltages();
    ///////////////////////////////////////////////////////////////////////////////

    check_button();
    check_rpi();
    check_sms();
    delay(1000);
  }
 }
///////////////////////////////////////////////////////////////////////////////




///////////////////////////////////////////////////////////////////////////////
// This function reads the programmed mobile number from the EEPROM
void get_mobile_number (void)
{
  int i = 0;
  char number[13];

  for (i=0 ; i < 12 ; i++)
  {
    number[i] = EEPROM.read(i);
  }
  number[12] = '\0';
  strcpy(mobile_number, number);
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
// This function programs a new mobile number into the EEPROM
void program_new_mobile_number(const char* number)
{
  Serial.println("Programming new mobile number");
  int i=0;

  for (i=0 ; i < 12 ; i++)
  {
    EEPROM.write(i, number[i]);
    delay(1000);
  }
  Serial.println("Done");
  // Serial.println("Done. Reading back from EEPROM....");
  // get_mobile_number();
  // Serial.print("The number programmed in EEPROM is: ");
  // Serial.println(mobile_number);
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
int setup_SIM800L (void)
{
  int i = 0;
  int k = 0;
  char response[100] = {0};
 
  delay(1000);
  Serial.println("Checking communication with SIM800L module...");

  // Throw away first read
  Serial_SIM800L.println("AT");
  delay(1000);    
  clear_SIM800L_buffer();
 
  start_timer(180);
  while (check_timer())
  {
    k = 0;
    i = 0;
    delay(1000);   

    Serial.println("Sending command: AT...");
    Serial_SIM800L.println("AT");
    delay(1000);    
  
    while (Serial_SIM800L.available())
    {
      response[i] = Serial_SIM800L.read();
      i++;
    }    
    while (k < i)
    {
      if (response[k] == 'O')
      {
        if (response[k+1] == 'K')
        {
          Serial.println("Communication with SIM800L module successful");
          Serial.println("Configuring TEXT mode");
          Serial_SIM800L.println("AT+CMGF=1");
          delay(1000);
          clear_SIM800L_buffer();


          Serial.println("Configuring sms message storage area");
          Serial_SIM800L.println("AT+CPMS=\"SM\",\"SM\",\"SM\"");
          delay(1000);
          
          clear_SIM800L_buffer();

          Serial.println("Setting SMS memory storage area");
          Serial_SIM800L.println("AT+CNMI=2,2,0,0,0"); 
          delay(1000);
          clear_SIM800L_buffer();
          
          Serial.println("Enabling local time stamp retrieval");
          Serial_SIM800L.println("AT+CLTS=1"); 
          delay(1000);
          clear_SIM800L_buffer();

          Serial.println("Saving settings");
          Serial_SIM800L.println("AT&W"); 
          delay(1000);
          clear_SIM800L_buffer();
          return 1;       
        }
      }
      k++;
    }
  }
}
///////////////////////////////////////////////////////////////////////////////


 


///////////////////////////////////////////////////////////////////////////////
void update_date_time (void)
{
  int i = 0;
  int k = 0;
  char date_time[15] = {0};
  char response[100] = {0};

  delay(10);
  clear_SIM800L_buffer();

  Serial_SIM800L.println("AT+CCLK?");
  delay(1000);
  while (Serial_SIM800L.available())
  {
    response[i] = Serial_SIM800L.read();
    i++;
  }
  
  /////////////////////////////////////////////////////////////////////////////
  // Serial1.println("response: ");
  // Serial1.println(response);
  /////////////////////////////////////////////////////////////////////////////
  
  
  // If the device did not respond, date_time will be all null
  date_time[0] = response[19];    // Y
  date_time[1] = response[20];    // Y
  date_time[2] = response[22];    // M
  date_time[3] = response[23];    // M
  date_time[4] = response[25];    // D
  date_time[5] = response[26];    // D
  date_time[6] = response[28];    // H
  date_time[7] = response[29];    // H
  date_time[8] = response[31];    // M
  date_time[9] = response[32];    // M
  date_time[10] = response[34];   // S
  date_time[11] = response[35];   // S
  date_time[12] = '\0';


  // Serial1.println("date_time");
  // Serial1.println(date_time);


  //  Check if year is 2004 - This is the default when the current time can not be found. This can change
  //Serial.print(date_time);
  if (date_time[0] == '0')
  {
    if (date_time[1] == '4')
    {
      strcpy(date_time_formatted, "UNAVAILABLE");
      return;
    }
  
  }
  else if (date_time[0] == NULL)  
  {
    //Serial.println("datetime is null");
    strcpy(date_time_formatted, "UNAVAILABLE");
    return;
  }
  
  // 20YYMMDDHHmmSS

  date_time_formatted[0] = '2';
  date_time_formatted[1] = '0';
  date_time_formatted[2] = date_time[0];
  date_time_formatted[3] = date_time[1];
  
  //month  
  date_time_formatted[5] = date_time[2];
  date_time_formatted[6] = date_time[3];
  
  //day
  date_time_formatted[8] = date_time[4];
  date_time_formatted[9] = date_time[5];

  //hour
  date_time_formatted[11] = date_time[6];
  date_time_formatted[12] = date_time[7];

  //min
  date_time_formatted[14] = date_time[8];
  date_time_formatted[15] = date_time[9];

  //sec
  date_time_formatted[17] = date_time[10];
  date_time_formatted[18] = date_time[11];


  // Check if "UNAVAILABLE" is present in boot_time_formatted
  if (strstr(boot_time_formatted, "UNAVAILABLE") != NULL) 
  {
    if (strstr(date_time_formatted, "UNAVAILABLE") == NULL)
    {
      strcpy(boot_time_formatted, date_time_formatted);
    }
  }
}
///////////////////////////////////////////////////////////////////////////////




///////////////////////////////////////////////////////////////////////////////
void get_temperature (void)
{
  int adc_temperature =  analogRead(pin_temp);
  delay(100);
  adc_temperature =  analogRead(pin_temp);
  
  float_temperature = ((adc_temperature/1023.0)*5000.0)/10.0;
}

void check_temperature (void)
{
  if (float_temperature > 50.0)
  {
    sms_alert("WARNING: Ambient temperature greater than 50 degrees C!");
  }
  else
  {
    Serial.println("\t Temperature OK ");
  }
  Serial.print("\n");
}
///////////////////////////////////////////////////////////////////////////////





///////////////////////////////////////////////////////////////////////////////
void get_voltages (void)
{
  int adc_4V =  analogRead(pin_4V);
  delay(10);
  adc_4V =  analogRead(pin_4V);
  delay(10);
  
  int adc_5V =  analogRead(pin_5V);
  delay(10);
  adc_5V =  analogRead(pin_5V);
  delay(10);
  
  int adc_12V =  analogRead(pin_12V);
  delay(10);
  adc_12V =  analogRead(pin_12V);
  delay(10);

  int adc_24V =  analogRead(pin_24V);
  delay(10);
  adc_24V =  analogRead(pin_24V);
  delay(10);

  //Multipliers: (R1+R2)/R2 4V Does not use a voltage divider
  float multiplier_5V  = 1.25;
  float multiplier_12V  = 2.79;  
  float multiplier_24V = 5.82;
  
  float_4V  = (adc_4V/1023.0)*5.0;
  float_5V  = ((adc_5V/1023.0)*5.0)*multiplier_5V;
  float_12V  = ((adc_12V/1023.0)*5.0)*multiplier_12V;  
  float_24V = ((adc_24V/1023.0)*5.0)*multiplier_24V;
}
///////////////////////////////////////////////////////////////////////////////




///////////////////////////////////////////////////////////////////////////////
void check_voltages (void)
{
  Serial.print("4V Supply: \t\t");
  Serial.print(float_4V);
  Serial.print(" V");
  if (float_4V > 4.4)
  {
    Serial.println("\t\t SIM800L voltage too high");
    sms_alert("ALERT: 4V supply too high");
  }
  else if (float_4V < 3.4)
  {
    Serial.println("\t\t SIM800L voltage too low");
    sms_alert("ALERT: 4V supply too low");
  }
  else
  {
    Serial.println("\t\t Voltage OK");
  }

 
  Serial.print("5V (Raspberry Pi): \t");
  Serial.print(float_5V);
  Serial.print(" V");
  if (float_5V > 5.5)
  {
    Serial.println("\t\t Raspberry Pi supply voltage too high");
    sms_alert("ALERT: 5V (Rpi) supply too high");
  }
  else if (float_5V < 4.75)
  {
    Serial.println("\t\t Raspberry Pi supply voltage too low");
    sms_alert("ALERT: 5V (Rpi) supply too low");
  }
  else
  {
    Serial.println("\t\t Voltage OK");
  }
  
  Serial.print("12V Supply (Scales): \t");
  Serial.print(float_12V);
  Serial.println(" V");
  if (float_12V > 13.2)
  {
    Serial.println("\t\t Battery voltage too high");
    sms_alert("ALERT: 12V (Scales) supply too high");
  }
  else if (float_12V < 10.8)
  {
    Serial.println("\t\t Battery voltage too low");
    sms_alert("ALERT: 12V (Scales) supply too low");
  }
  else
  {
    Serial.println("\t\t Voltage OK");
  }

  Serial.print("24V Solar Supply: \t");
  Serial.print(float_24V);
  Serial.print(" V");
  if (float_24V > 28.8)
  {
    Serial.println("\t\t Battery voltage too high");
    sms_alert("ALERT: 24V Solar supply too high");
  }
  else if (float_24V < 24.0)
  {
    Serial.println("\t\t Battery voltage too low");
    sms_alert("ALERT: 24V Solar supply too low");
  }
  else
  {
    Serial.println("\t\t Voltage OK");
  }
  Serial.print("\n");
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void check_button (void)
{
  if (digitalRead(pin_button) == 0)
  {
    if (rpi_flag == 1)
    {
      Serial.println("Button has been pressed. Shutting down...");
      beep(2);
      rpi_power_on_off();
      rpi_flag = 0;
    }
    else
    {
      Serial.println("Button has been pressed. Powering up...");
      beep(1);
      rpi_power_on_off();
      rpi_flag = 1;
    }
  }  
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void read_pi (char rpi_message[200])
{
  Serial1.readBytesUntil('@', rpi_message, 199);
  rpi_message[199] = '\0';  // Null-terminate the string
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void check_rpi (void)
{
  int k=0;
  int i=0;
  char rpi_message[200] = {0};

  
  if (Serial1.available())
  {

    // Data is available (or busy being sent)
    // Delay 100ms to let it potentially finish
    delay(100);

    // Read whatever came from the pi into rpi_message
    read_pi(rpi_message);
    //Serial1.println("rpi_message"); 
    //Serial1.println(rpi_message); 

    /* 
    A command starts with the character '$' and ends with the character '@'
    The middle character is the command. 
      R: Request for a status report from the Monitor to the Pi
      S: Request to send the Rpi report to the Monitor
      Q: Rpi wants to send a sms
      L: Rpi direct communication with SIM800L
      C: Rpi is checking if there is a terminal command to be executed.
    */
    
    //Check if the rpi is sending a command
    if (rpi_message[0] == '$') // Raspberry Pi command
    {     
      if (rpi_message[1] == 'R')
      {
        pi_cmd_R();
      }
      else if (rpi_message[1] == 'S')
      {
        pi_cmd_S();
      }
      else if (rpi_message[1] == 'Q')
      {
        pi_cmd_Q();
      }
      else if (rpi_message[1] == 'L')
      {
        pi_cmd_L();
      }
      else if (rpi_message[1] == 'P')
      {
        pi_cmd_P();
      }
      else if (rpi_message[1] == 'C')
      {
        pi_cmd_C();        
      }
      else
      {
        Serial.print("Unknown command - Received: "); 
        Serial.println(rpi_message); 
      }
    }
    else
    {
      Serial.print("Data received from rpi but not a command - Received: "); 
      Serial.println(rpi_message); 
    }
  }
}
///////////////////////////////////////////////////////////////////////////////
  

///////////////////////////////////////////////////////////////////////////////
void pi_cmd_R (void)
{
  // Raspberry Pi is requesting status report from Monitor
  send_status_report();
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void pi_cmd_S (void)
{
  // Raspberry Pi wants to send its status report
  Serial1.println("ACK$S");
  read_pi(rpi_status);
}  
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void pi_cmd_Q ()
{  
  char sms_message_to_send[200] = {0};
  Serial1.println("ACK$Q");
  read_pi(sms_message_to_send);
  sms(sms_message_to_send);
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void pi_cmd_L (void)
{
  // Raspberry Pi requesting to communicate directly with SIM800L
  Serial1.println("Entering SIM800L Mode...");
  rpi_SIM800L();
  Serial1.println("System in Normal Operating Mode");
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
// For Debugging: To send the Rpi report back to the Rpi                     //
///////////////////////////////////////////////////////////////////////////////
void pi_cmd_P (void)
{
  Serial1.println("Raspberry Pi Status Report:");
  Serial1.println("------------------------------------");
  Serial1.println(rpi_status);
  Serial1.println("------------------------------------");
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
// BETA: Will allow basic terminal commands to be sent to Pi via SMS         //
///////////////////////////////////////////////////////////////////////////////
void pi_cmd_C (void)
{

  // If the monitor has received a command for the Pi to execute, the flag will be set
  // The command is stored in the 'rpi_command' global char array
  if (rpi_command_flag == 1)
  {
    Serial1.println(rpi_command);
    memset(rpi_command, 0, sizeof(rpi_command));
    rpi_command_flag = 0;
  }
}
///////////////////////////////////////////////////////////////////////////////
 


///////////////////////////////////////////////////////////////////////////////
void start_timer(unsigned long sec)
{
  timer_val = sec;
  timer_start_ms = millis();
}
///////////////////////////////////////////////////////////////////////////////
int check_timer (void)
{
  
  // Timer has elapsed
  if (abs(  (millis() - timer_start_ms)/1000  ) > timer_val) 
  {
    timer_start_ms = 0;
    return 0;
  }
  
  // Timer still running
  else
  {
    return 1;
  }
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void send_status_report (void)
{
    Serial.println("Sending status report");
    Serial1.println ("-------------------------------------------------------");
    Serial1.println ("           Start of Arduino Status Report              ");
    Serial1.println ("-------------------------------------------------------");


    // Serial1.print("SIM800L connected to: ");
    // grab 'vodacom' from AT command
  
    
    Serial1.print("Arduino boot time: \t");
    Serial1.println(boot_time_formatted);

    Serial1.print("Arduino system time: \t");
    update_date_time();
    Serial1.println(date_time_formatted);

    Serial1.print("Stored Mobile Number: \t");
    Serial1.println(mobile_number);

    Serial1.print("Ambient temperature: \t");
    Serial1.print(float_temperature);
    Serial1.print(" deg C");      
    if (float_temperature > 50.0)
    {
      Serial1.println("\t Temperature high");
    }
    else
    {
      Serial1.println("\t Temperature OK ");
    }

    Serial1.print("4V SIM800L Supply: \t");
    Serial1.print(float_4V);
    Serial1.print(" V");
    if (float_4V > 4.4)
    {
      Serial1.println("\t\t SIM800L voltage too high");
    }
    else if (float_4V < 3.4)
    {
      Serial1.println("\t\t SIM800L voltage too low");
    }
    else
    {
      Serial1.println("\t\t Voltage OK");
    }

    Serial1.print("5V (Raspberry Pi): \t");
    Serial1.print(float_5V);
    Serial1.print(" V");
    if (float_5V > 5.5)
    {
      Serial1.println("\t\t Raspberry Pi supply voltage too high");
    }
    else if (float_5V < 4.75)
    {
      Serial1.println("\t\t Raspberry Pi supply voltage too low");
    }
    else
    {
      Serial1.println("\t\t Voltage OK");
    }

    Serial1.print("12V (Router, scales): \t");
    Serial1.print(float_12V);
    Serial1.print(" V");
    if (float_12V > 13.1)
    {
      Serial1.println("\t\t Battery voltage too high");
    }
    else if (float_24V < 11.5)
    {
      Serial1.println("\t\t Battery voltage too low");
    }
    else
    {
      Serial1.println("\t\t Voltage OK");
    }
    
    Serial1.print("24V Solar Supply: \t");
    Serial1.print(float_24V);
    Serial1.print(" V");
    if (float_24V > 28.8)
    {
      Serial1.println("\t\t Battery voltage too high");
    }
    else if (float_24V < 24.0)
    {
      Serial1.println("\t\t Battery voltage too low");
    }
    else
    {
      Serial1.println("\t\t Voltage OK");
    }
   
    Serial1.println ("-------------------------------------------------------");    
    Serial1.println ("          End of Arduino Status Report          ");
    Serial1.println ("-------------------------------------------------------");
    Serial.println("Status report sent");
    clear_Serial1_buffer();
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void check_sms (void)
{
  char response[300] = {0};
  
  char sender_mobile_number[13] = {0};

  //char response[160] = {0};
  int i=0;
  int k=0;
  
  while (Serial_SIM800L.available())
  {
    response[i] = Serial_SIM800L.read();
    delay(100);
    i++;
  }

  if (response[2] == '+')
  {
    if (response[3] == 'C')
    {
      if (response[4] == 'M')
      {
        if (response[5] == 'T')
        {
          Serial1.println("SMS received");
          Serial1.println(response);
  
          if (response[50] == 'C' || response[50] == 'c')
          {
            if (response[51] == 'M' || response[51] == 'm')
            {
              if (response[52] == 'D' || response[52] == 'd')
              {
                if (response[53] == ':')
                {
                  Serial1.print("Command received: ");
                  Serial1.println(response[54]);
                  if (response[54] == 'R' || response[54] == 'r')
                  {
                    cmd_R();
                  }                    
                  else if (response[54] == 'U' || response[54] == 'u')     
                  {
                    cmd_U(response);
                  }
                  else if (response[54] == 'S' || response[54] == 's')     
                  {
                    cmd_S();
                  }
                  else if (response[54] == 'P' || response[54] == 'p')     
                  {
                    cmd_P();
                  }
                  else if (response[54] == 'M' || response[54] == 'm')     
                  {
                    cmd_M(response);
                  }
                  else if (response[54] == 'X' || response[54] == 'x')     
                  {
                    sms ("Turning off sms notifications. Send cmd:y to activate again.");
                    sms_on = 0;
                  }
                  else if (response[54] == 'Y' || response[54] == 'y')     
                  {
                    sms_on = 1;
                    sms ("sms notifications have been turned on.");

                  }
                  else if (response[54] == 'C' || response[54] == 'c')     
                  {
                    cmd_C(response);
                  }

                  else
                  {
                    Serial.println("Unknown command");
                  }
                }
              }
            }
          }
        }
      }
    }
  }
  clear_SIM800L_buffer();
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
// Reboot Raspberry pi
// dtoverlay=gpio-shutdown,active_low=1,debounce=1000 in /boot/config.txt
void cmd_R()
{
  sms("A command to reboot the system was received. The operation should take approxiamtely a minute to complete");
  Serial.println("Rebooting System...");
  Serial.println("Shutting down...");
  // make pin low and wait 20 sec for pi to shut down
  rpi_power_on_off();
  delay(20000);
  // make pin low again to power up pi
  Serial.println("Powering up...");
  rpi_power_on_off();
  // wait 30 sec for pi to boot up
  delay(30000);
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
// Update the system's date and time variables
void cmd_U(char* response)
{

  Serial1.print("BEFORE: boot time formatted: ");
  Serial1.println(boot_time_formatted);
  Serial1.print("BEFORE: date time formatted: ");
  Serial1.println(date_time_formatted);
  
  update_date_time();
  
  Serial1.print("AFTER: boot time formatted: ");
  Serial1.println(boot_time_formatted);
  Serial1.print("After: date time formatted: ");
  Serial1.println(date_time_formatted);
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void cmd_S()
{
  sms_status_report();
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void cmd_P()
{
  rpi_power_on_off();
  sms("Power ON/OFF received. Powering on/off...");
}
///////////////////////////////////////////////////////////////////////////////


  
///////////////////////////////////////////////////////////////////////////////
void cmd_M (char* response)
{
  int j=0;
  char new_number[13] = {0};

  //sms(response);

  Serial.println("Received command to change mobile number");
  for (j=0 ; j < 12 ; j++)
  {
    new_number[j] = response[55+j];
  }
  Serial.print("New number: ");
  Serial.println(new_number);

  if (new_number[0] != '+' || new_number[1] != '2' || new_number[2] != '7') // requirement for correctly formatted SA number
  {
    Serial.println("Invalid mobile number. Sending sms to saved number.");
    sms("A request to change the mobile number has been received. The mobile number provided is not valid. Ensure that the mobile number starts with +27");
  }
  else if (strcmp(mobile_number,new_number) == 0) // if the new number is the same as the old number  
  {
    Serial.println("Same mobile number");
    sms("A request to change the mobile number has been received. As the new number is the same as the currently saved number, no changes will be made");
  }
  else
  {
    strcpy(old_mobile_number,mobile_number);
    program_new_mobile_number(new_number);
    Serial.println("Sending sms to old number");
    sms("Mobile number has been succesfully changed. This mobile number will no longer be used in future.");
    get_mobile_number();
    Serial.println("Sending sms to new number");
    sms("Mobile number has been succesfully changed. This is the new mobile number that will be used in future.");
    Serial.println("Mobile number successfully changed");
  }
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void cmd_C (char* response)
{
  int j=0;
  rpi_command_flag = 1;

  for (j=0 ; j < 100 ; j++)
  {
    rpi_command[j] = response[55+j];
  }
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
// Note: If this function is not working properly, ensure the RX buffer size has been increased (use 200)

void sms_status_report (void)
{
  //Serial.println("Sending sms");
  char sms_message[160] = {0};

  strcat (sms_message, "Boot:");
  strcat (sms_message, boot_time_formatted);
  strcat (sms_message, "\n");

  strcat (sms_message, "Temp:");
  char temperature_string[6] = {0};
  dtostrf(float_temperature, 4, 1, temperature_string); 
  strcat (sms_message, temperature_string);
  strcat (sms_message, "\n");

  strcat (sms_message, "24V:");
  char solar_24V_string[6] = {0};
  dtostrf(float_24V, 4, 1, solar_24V_string); 
  strcat (sms_message, solar_24V_string);
  strcat (sms_message, "\n");
    
  strcat (sms_message, "12V:");
  char LTE_12V_string[6] = {0};
  dtostrf(float_12V, 4, 1, LTE_12V_string); 
  strcat (sms_message, LTE_12V_string);
  strcat (sms_message, "\n");

  strcat (sms_message, "5V:");
  char rpi_5V_string[5] = {0};
  dtostrf(float_5V, 3, 1, rpi_5V_string); 
  strcat (sms_message, rpi_5V_string);
  strcat (sms_message, "\n");
  //
  strcat (sms_message, "4V:");
  char sim_4V_string[5] = {0};
  dtostrf(float_4V, 3, 1, sim_4V_string); 
  strcat (sms_message, sim_4V_string);
  strcat (sms_message, "\n");

  strcat (sms_message, "Rpi: ");
  strcat (sms_message, rpi_status);
  strcat (sms_message, "\n");

  sms(sms_message);
 
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
// This function sends an alert via sms
void sms_alert (char* sms_alert_message)
{
  // Timer not running
  if (check_timer() == 0)
  {
    sms(sms_alert_message);

    // Dont send another alert for an hour
    start_timer(3600);
  }
}
///////////////////////////////////////////////////////////////////////////////


//AT+CMGS="+27728391080"

///////////////////////////////////////////////////////////////////////////////
// This function sends an sms
void sms (char* sms_message)
{
  if (sms_on == 0)
  {
    return;
  }
  
  clear_SIM800L_buffer();
  
  Serial_SIM800L.print("AT+CMGS=\"");
  Serial_SIM800L.print(mobile_number);
  Serial_SIM800L.println("\"");
  delay(1000);
  
  clear_SIM800L_buffer();

  Serial_SIM800L.print(sms_message);
  Serial_SIM800L.write(26);
  
  delay(10000);
  clear_SIM800L_buffer();        
  Serial1.println("sms sent");
}
///////////////////////////////////////////////////////////////////////////////


///////////////////////////////////////////////////////////////////////////////
void rpi_power_on_off (void)
{
  digitalWrite(pin_rpi_shutdown, LOW);
  delay(1200);
  digitalWrite(pin_rpi_shutdown, HIGH);
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void led_on (void)
{
  digitalWrite(pin_led, HIGH);
}
void led_off (void)
{
  digitalWrite(pin_led, LOW);
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void beep (int num)
{
  int i=0;
  for (i=0 ; i < num ; i++)
  {
    digitalWrite(pin_buzzer, HIGH);
    delay(300);
    digitalWrite(pin_buzzer, LOW);
    delay(300);
  }
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void rpi_SIM800L()
{
  // Start by clearing the Serial1 buffer
  clear_Serial1_buffer();

  // Now wait for a string to be sent over the serial port (from the rpi)
  Serial1.println("Connected to SIM800L. Type exit to return to normal Monitor Mode");
  while(1)
  {
    char buffer[50] = {0};  // Allocate a buffer to store the received data
    if (Serial1.available())
    {
      int bytesRead = Serial1.readBytesUntil('\r', buffer, sizeof(buffer) - 1);
    
      if (strcmp(buffer, "exit") == 0)
      {
        Serial1.println("Exiting SIM800L Mode...");
        return;
      }
      else
      {
        Serial_SIM800L.println(buffer);
        delay(100);
      }

      if (Serial_SIM800L.available())
      {

        while(Serial_SIM800L.available()) 
        {
          //Forward everything received from the SIM800L, to the rpi
          Serial1.write(Serial_SIM800L.read());  
        }
      }
    }
  }
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void clear_SIM800L_buffer (void)
{
  while (Serial_SIM800L.available())
  {
    Serial_SIM800L.read();
    delay(10);
  }
}
///////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////////////
void clear_Serial1_buffer (void)
{
  while (Serial1.available())
  {
    Serial1.read();
    delay(10);
  }
}
///////////////////////////////////////////////////////////////////////////////