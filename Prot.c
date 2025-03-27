#include "main.h"
#include <string.h>

extern UART_HandleTypeDef huart2;

#define RX_BUF_SIZE 64
char rx_buffer[RX_BUF_SIZE];
uint8_t rx_byte;
uint8_t idx = 0;

int main(void)
{
  HAL_Init();
  SystemClock_Config();
  MX_GPIO_Init();
  MX_USART2_UART_Init();

  while (1)
  {
    HAL_UART_Receive(&huart2, &rx_byte, 1, HAL_MAX_DELAY);

    if (rx_byte == '\r' || rx_byte == '\n') {
      if (idx > 0) {
        rx_buffer[idx] = '\0'; // Null terminate
        HAL_UART_Transmit(&huart2, (uint8_t*)rx_buffer, idx, HAL_MAX_DELAY);
        HAL_UART_Transmit(&huart2, (uint8_t*)"\r\n", 2, HAL_MAX_DELAY);
        idx = 0;
      }
    } 
    else if (idx < RX_BUF_SIZE - 1) {
      rx_buffer[idx++] = rx_byte;
    }
  }
}
