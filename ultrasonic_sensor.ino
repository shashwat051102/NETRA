/*
 * Ultrasonic Sensor (HC-SR04) with Arduino Uno
 * 
 * Pin Configuration:
 * VCC  -> 5V
 * GND  -> GND
 * TRIG -> D9
 * ECHO -> D10
 */

const int trigPin = 9;
const int echoPin = 10;

long duration;
float distance;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Configure pins
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  Serial.println("Ultrasonic Sensor Ready");
}

void loop() {
  // Clear the trigPin
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  // Trigger the sensor by setting trigPin HIGH for 10 microseconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Read the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(echoPin, HIGH);
  
  // Calculate the distance (Speed of sound: 343 m/s or 0.0343 cm/μs)
  // Distance = (Time × Speed) / 2
  distance = duration * 0.0343 / 2;
  
  // Send distance to serial port
  Serial.println(distance);
  
  // Small delay before next reading
  delay(100);
}
