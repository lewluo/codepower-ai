#include "wifi_board.h"
#include "codecs/no_audio_codec.h"
#include "display/lcd_display.h"
#include "system_reset.h"
#include "application.h"
#include "button.h"
#include "config.h"
#include "power_save_timer.h"
#include "led/single_led.h"
#include "assets/lang_config.h"
#include "power_manager.h"

#include <esp_log.h>
#include <esp_lcd_panel_vendor.h>
#include <wifi_station.h>

#include <driver/rtc_io.h>
#include <esp_sleep.h>
#include <esp_timer.h>

#define TAG "XINGZHI_CUBE_1_54TFT_WIFI"

class XINGZHI_CUBE_1_54TFT_WIFI : public WifiBoard {
private:
    static constexpr int kBootButtonDoubleClickWindowMs = 250;

    Button boot_button_;
    Button volume_up_button_;
    Button volume_down_button_;
    SpiLcdDisplay* display_;
    PowerSaveTimer* power_save_timer_;
    PowerManager* power_manager_;
    esp_lcd_panel_io_handle_t panel_io_ = nullptr;
    esp_lcd_panel_handle_t panel_ = nullptr;
    esp_timer_handle_t boot_button_hold_timer_ = nullptr;
    bool boot_button_pressed_ = false;
    bool boot_button_listening_started_ = false;
    bool boot_button_skip_release_ = false;
    int64_t boot_button_last_tap_time_us_ = 0;

    void InitializeBootButtonTimer() {
        esp_timer_create_args_t timer_args = {
            .callback = [](void* arg) {
                auto* board = static_cast<XINGZHI_CUBE_1_54TFT_WIFI*>(arg);
                board->HandleBootButtonHoldTimeout();
            },
            .arg = this,
            .dispatch_method = ESP_TIMER_TASK,
            .name = "boot_btn_hold",
            .skip_unhandled_events = true,
        };
        ESP_ERROR_CHECK(esp_timer_create(&timer_args, &boot_button_hold_timer_));
    }

    void HandleBootButtonHoldTimeout() {
        if (!boot_button_pressed_ || boot_button_listening_started_) {
            return;
        }
        auto& app = Application::GetInstance();
        if (app.GetDeviceState() == kDeviceStateStarting && !WifiStation::GetInstance().IsConnected()) {
            return;
        }
        boot_button_listening_started_ = true;
        app.StartListening();
    }

    void ToggleConversationMode() {
        auto& app = Application::GetInstance();
        app.ToggleConversationMode();
        GetDisplay()->ShowNotification(app.GetConversationModeName());
    }

    void InitializePowerManager() {
        power_manager_ = new PowerManager(GPIO_NUM_38);
        power_manager_->OnChargingStatusChanged([this](bool is_charging) {
            if (is_charging) {
                power_save_timer_->SetEnabled(false);
            } else {
                power_save_timer_->SetEnabled(true);
            }
        });
    }

    void InitializePowerSaveTimer() {
        rtc_gpio_init(GPIO_NUM_21);
        rtc_gpio_set_direction(GPIO_NUM_21, RTC_GPIO_MODE_OUTPUT_ONLY);
        rtc_gpio_set_level(GPIO_NUM_21, 1);

        power_save_timer_ = new PowerSaveTimer(-1, 60, 300);
        power_save_timer_->OnEnterSleepMode([this]() {
            GetDisplay()->SetPowerSaveMode(true);
            GetBacklight()->SetBrightness(1);
        });
        power_save_timer_->OnExitSleepMode([this]() {
            GetDisplay()->SetPowerSaveMode(false);
            GetBacklight()->RestoreBrightness();
        });
        power_save_timer_->OnShutdownRequest([this]() {
            ESP_LOGI(TAG, "Shutting down");
            rtc_gpio_set_level(GPIO_NUM_21, 0);
            // 启用保持功能，确保睡眠期间电平不变
            rtc_gpio_hold_en(GPIO_NUM_21);
            esp_lcd_panel_disp_on_off(panel_, false); //关闭显示
            esp_deep_sleep_start();
        });
        power_save_timer_->SetEnabled(true);
    }

    void InitializeSpi() {
        spi_bus_config_t buscfg = {};
        buscfg.mosi_io_num = DISPLAY_SDA;
        buscfg.miso_io_num = GPIO_NUM_NC;
        buscfg.sclk_io_num = DISPLAY_SCL;
        buscfg.quadwp_io_num = GPIO_NUM_NC;
        buscfg.quadhd_io_num = GPIO_NUM_NC;
        buscfg.max_transfer_sz = DISPLAY_WIDTH * DISPLAY_HEIGHT * sizeof(uint16_t);
        ESP_ERROR_CHECK(spi_bus_initialize(SPI3_HOST, &buscfg, SPI_DMA_CH_AUTO));
    }

    void InitializeButtons() {
        boot_button_.OnPressDown([this]() {
            power_save_timer_->WakeUp();
            boot_button_pressed_ = true;
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateStarting && !WifiStation::GetInstance().IsConnected()) {
                ResetWifiConfiguration();
                boot_button_pressed_ = false;
                return;
            }

            int64_t now_us = esp_timer_get_time();
            if (boot_button_last_tap_time_us_ != 0 &&
                (now_us - boot_button_last_tap_time_us_) <= kBootButtonDoubleClickWindowMs * 1000LL) {
                boot_button_last_tap_time_us_ = 0;
                boot_button_skip_release_ = true;
                ToggleConversationMode();
                return;
            }

            esp_timer_stop(boot_button_hold_timer_);
            ESP_ERROR_CHECK(esp_timer_start_once(
                boot_button_hold_timer_,
                kBootButtonDoubleClickWindowMs * 1000ULL
            ));
        });

        boot_button_.OnPressUp([this]() {
            power_save_timer_->WakeUp();
            boot_button_pressed_ = false;
            esp_timer_stop(boot_button_hold_timer_);

            if (boot_button_skip_release_) {
                boot_button_skip_release_ = false;
                return;
            }

            auto& app = Application::GetInstance();
            if (boot_button_listening_started_) {
                boot_button_listening_started_ = false;
                boot_button_last_tap_time_us_ = 0;
                app.StopListening();
                return;
            }

            boot_button_last_tap_time_us_ = esp_timer_get_time();
        });

        volume_up_button_.OnClick([this]() {
            power_save_timer_->WakeUp();
            auto& app = Application::GetInstance();
            app.SendControlMessage("accept");
            GetDisplay()->ShowNotification("Accept");
        });

        volume_up_button_.OnLongPress([this]() {
            power_save_timer_->WakeUp();
            auto& app = Application::GetInstance();
            app.SendControlMessage("accept");
            GetDisplay()->ShowNotification("Accept");
        });

        volume_down_button_.OnClick([this]() {
            power_save_timer_->WakeUp();
            auto& app = Application::GetInstance();
            app.SendControlMessage("reject");
            GetDisplay()->ShowNotification("Reject");
        });

        volume_down_button_.OnLongPress([this]() {
            power_save_timer_->WakeUp();
            auto& app = Application::GetInstance();
            app.SendControlMessage("reject");
            GetDisplay()->ShowNotification("Reject");
        });
    }

    void InitializeSt7789Display() {
        ESP_LOGD(TAG, "Install panel IO");
        esp_lcd_panel_io_spi_config_t io_config = {};
        io_config.cs_gpio_num = DISPLAY_CS;
        io_config.dc_gpio_num = DISPLAY_DC;
        io_config.spi_mode = 3;
        io_config.pclk_hz = 80 * 1000 * 1000;
        io_config.trans_queue_depth = 10;
        io_config.lcd_cmd_bits = 8;
        io_config.lcd_param_bits = 8;
        ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi(SPI3_HOST, &io_config, &panel_io_));

        ESP_LOGD(TAG, "Install LCD driver");
        esp_lcd_panel_dev_config_t panel_config = {};
        panel_config.reset_gpio_num = DISPLAY_RES;
        panel_config.rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB;
        panel_config.bits_per_pixel = 16;
        ESP_ERROR_CHECK(esp_lcd_new_panel_st7789(panel_io_, &panel_config, &panel_));
        ESP_ERROR_CHECK(esp_lcd_panel_reset(panel_));
        ESP_ERROR_CHECK(esp_lcd_panel_init(panel_));
        ESP_ERROR_CHECK(esp_lcd_panel_swap_xy(panel_, DISPLAY_SWAP_XY));
        ESP_ERROR_CHECK(esp_lcd_panel_mirror(panel_, DISPLAY_MIRROR_X, DISPLAY_MIRROR_Y));
        ESP_ERROR_CHECK(esp_lcd_panel_invert_color(panel_, true));

        display_ = new SpiLcdDisplay(panel_io_, panel_, DISPLAY_WIDTH, DISPLAY_HEIGHT, DISPLAY_OFFSET_X, DISPLAY_OFFSET_Y, 
            DISPLAY_MIRROR_X, DISPLAY_MIRROR_Y, DISPLAY_SWAP_XY);
    }

public:
    XINGZHI_CUBE_1_54TFT_WIFI() :
        boot_button_(BOOT_BUTTON_GPIO),
        volume_up_button_(VOLUME_UP_BUTTON_GPIO),
        volume_down_button_(VOLUME_DOWN_BUTTON_GPIO) {
        InitializePowerManager();
        InitializePowerSaveTimer();
        InitializeSpi();
        InitializeBootButtonTimer();
        InitializeButtons();
        InitializeSt7789Display();
        GetBacklight()->RestoreBrightness();
    }

    virtual ~XINGZHI_CUBE_1_54TFT_WIFI() {
        if (boot_button_hold_timer_ != nullptr) {
            esp_timer_stop(boot_button_hold_timer_);
            esp_timer_delete(boot_button_hold_timer_);
        }
    }

    virtual AudioCodec* GetAudioCodec() override {
        static NoAudioCodecSimplex audio_codec(AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_SPK_GPIO_BCLK, AUDIO_I2S_SPK_GPIO_LRCK, AUDIO_I2S_SPK_GPIO_DOUT, AUDIO_I2S_MIC_GPIO_SCK, AUDIO_I2S_MIC_GPIO_WS, AUDIO_I2S_MIC_GPIO_DIN);
        return &audio_codec;
    }

    virtual Display* GetDisplay() override {
        return display_;
    }
    
    virtual Backlight* GetBacklight() override {
        static PwmBacklight backlight(DISPLAY_BACKLIGHT_PIN, DISPLAY_BACKLIGHT_OUTPUT_INVERT);
        return &backlight;
    }

    virtual bool GetBatteryLevel(int& level, bool& charging, bool& discharging) override {
        static bool last_discharging = false;
        charging = power_manager_->IsCharging();
        discharging = power_manager_->IsDischarging();
        if (discharging != last_discharging) {
            power_save_timer_->SetEnabled(discharging);
            last_discharging = discharging;
        }
        level = power_manager_->GetBatteryLevel();
        return true;
    }

    virtual void SetPowerSaveMode(bool enabled) override {
        if (!enabled) {
            power_save_timer_->WakeUp();
        }
        WifiBoard::SetPowerSaveMode(enabled);
    }
};

DECLARE_BOARD(XINGZHI_CUBE_1_54TFT_WIFI);
