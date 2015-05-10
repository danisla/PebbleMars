#include <pebble.h>
#include "PebbleMars.h"
#include "base64.h"
#include "ui.h"
#include "marstime.h"

uint8_t image_next_chunk_id;
bool image_chunk_marks[IMAGE_CHUNKS];
bool image_receiving;
bool hide_mars_time = 0;

static void image_mark_chunk(uint8_t);
static bool image_check_chunks();
static void image_start_transfer();
static void image_complete_transfer();

static uint32_t lmst_update_interval;

static AppTimer *g_timer;

static void update_mars_time_visibility() {
  layer_set_hidden((Layer*)lmst_layer, hide_mars_time);
  layer_set_hidden((Layer*)lmst_separator, hide_mars_time);
}

void send_app_message(SendCallback callback, void *data) {
  DictionaryIterator *iter;
  app_message_outbox_begin(&iter);

  callback(iter, data);
  dict_write_end(iter);

  app_message_outbox_send();
}

void send_uint8(DictionaryIterator *iter, void *data) {
  Tuplet *tuplet = (Tuplet*) data;
  dict_write_uint8(iter, tuplet->key, tuplet->integer.storage);
}

size_t process_string(char *str) {
  uint16_t input_len_bytes = strlen(str);
  uint16_t output_len_bytes = 4 * (input_len_bytes/3);

  output_len_bytes += output_len_bytes % 4;

  struct {
    uint8_t id;
    uint32_t bmp[IMAGE_CHUNK_SIZE];
  } __attribute__((__packed__)) image_chunk;

  decode_base64((uint8_t *) &image_chunk, (uint8_t *) str, input_len_bytes);

  if (image_chunk.id >= IMAGE_CHUNKS) {
    return 0;
  }

  size_t chunk_offset = image_chunk.id * IMAGE_CHUNK_SIZE;
  for (uint16_t i = 0; i < ARRAY_LENGTH(image_chunk.bmp); i++) {
    mars_image_set_dword(chunk_offset + i, image_chunk.bmp[i]);
  }

  image_mark_chunk(image_chunk.id);

  uint8_t next_row = image_next_chunk_id * IMAGE_CHUNK_SIZE / IMAGE_COLS;
  slide_progress_separator(next_row);
  mars_image_mark_dirty();

  return ARRAY_LENGTH(image_chunk.bmp);
}

void remote_image_data(DictionaryIterator *received) {
  Tuple *image_data_tuple;
  image_data_tuple = dict_find(received, KEY_IMAGE_DATA);
  if (image_data_tuple) {
    char *data = image_data_tuple->value->cstring;

    process_string(data);

    image_check_chunks();
  }
  else {
    if (DEBUG) APP_LOG(APP_LOG_LEVEL_WARNING, "Not a remote-image message");
  }
}

static void image_start_transfer() {
  image_receiving = true;
  image_next_chunk_id = 0;
  memset(image_chunk_marks, 0, sizeof(image_chunk_marks));
  Tuplet tuplet = TupletInteger(KEY_IMAGE_START, 0);
  send_app_message(send_uint8, &tuplet);
}

static void image_complete_transfer() {
  if (!image_receiving) {
   return;
  }
  image_receiving = false;
  Tuplet tuplet = TupletInteger(KEY_IMAGE_COMPLETE, 0);
  send_app_message(send_uint8, &tuplet);
}

static void image_mark_chunk(uint8_t chunk_id) {
  if (chunk_id >= image_next_chunk_id) {
    if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "mark next %d %d", (int) chunk_id, (int) image_next_chunk_id);
    image_next_chunk_id = chunk_id+1;
  }
  image_chunk_marks[chunk_id] = true;
}

static int16_t image_get_next_chunk_id() {
  for (uint8_t i = 0; i < image_next_chunk_id && i < IMAGE_CHUNKS; i++) {
    if (!image_chunk_marks[i]) {
      return i;
    }
  }
  if (image_next_chunk_id < IMAGE_CHUNKS) {
    return image_next_chunk_id;
  }
  return -1;
}

static bool image_check_chunks() {
  int16_t next_chunk_id = image_get_next_chunk_id();
  if (next_chunk_id < 0) {
    image_complete_transfer();
    return true;
  }

  if (next_chunk_id == image_next_chunk_id) {
    return false;
  }

  Tuplet tuplet = TupletInteger(KEY_IMAGE_REQUEST_CHUNK, next_chunk_id);
  send_app_message(send_uint8, &tuplet);
  return false;
}

void app_message_out_sent(DictionaryIterator *sent, void *context) {
  if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "out_sent");
}

void app_message_out_failed(DictionaryIterator *failed, AppMessageResult reason, void *context) {
  if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "out_failed reason=%d", reason);
}

void app_message_in_received(DictionaryIterator *received, void *context) {
  if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "in_received");

  Tuple *t;
  if ((t = dict_find(received, KEY_TEMPERATURE))) {
    if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "Temperature %s", t->value->cstring);
    set_info_text(KEY_TEMPERATURE, t->value->cstring);
  }
  if ((t = dict_find(received, KEY_REL_TIME))) {
    if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "Relative Time %s", t->value->cstring);
    set_info_text(KEY_REL_TIME, t->value->cstring);
  }
  if ((t = dict_find(received, KEY_INSTRUMENT))) {
    if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "Instrument %s", t->value->cstring);
    set_info_text(KEY_INSTRUMENT, t->value->cstring);
  }
  if ((t = dict_find(received, KEY_UTC))) {
    if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "UTC %s", t->value->cstring);
    set_info_text(KEY_UTC, t->value->cstring);
    // Start a new image when receiving UTC
    image_start_transfer();
  }
  if ((t = dict_find(received, KEY_FILENAME))) {
    if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "Filename %s", t->value->cstring);
    set_info_text(KEY_FILENAME, t->value->cstring);
  }
  if ((t = dict_find(received, KEY_IMAGE_DATA))) {
    remote_image_data(received);
    app_comm_set_sniff_interval(SNIFF_INTERVAL_REDUCED);
  }
  if ((t = dict_find(received, KEY_IMAGE_COMPLETE))) {
    // This is a query, but we'll stop for now
    image_complete_transfer();
  }
  if ((t = dict_find(received, KEY_TZ_OFFSET))) {
    int32_t value = t->value->int32;

    // Save value to persistent storage.
    int tz_key_status = persist_write_int(PERSIST_TZ_KEY, value);
    int tz_ttl_key_status = persist_write_int(PERSIST_TZ_TTL_KEY, time(NULL));

    if (tz_key_status < 0 || tz_ttl_key_status < 0) {
      if (DEBUG) APP_LOG(APP_LOG_LEVEL_ERROR, "Error writing to persistent storage, factory reset may be needed to recover.");
    }
    if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "TZ Offset from JS: %i, persist write status: %d,%d", (int)value, tz_key_status, tz_ttl_key_status);
  }
  if ((t = dict_find(received, KEY_HIDE_MARS_TIME))) {
    int32_t value = t->value->int32;

    hide_mars_time = value;

    // Save value to persistent storage.
    int key_status = persist_write_int(PERSIST_HIDE_MARS_TIME_KEY, value);

    if (key_status < 0) {
      if (DEBUG) APP_LOG(APP_LOG_LEVEL_ERROR, "Error writing to persistent storage, factory reset may be needed to recover.");
    }
    if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "Mars time hiding from JS: %i, persist write status: %d", (int)value, key_status);

    update_mars_time_visibility();

  }
}

void app_message_in_dropped(void *context, AppMessageResult reason) {
  if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "in_dropped reason=%d", reason);
}

static void handle_accel_tap(AccelAxisType axis, int32_t direction) {
  image_complete_transfer();
  Tuplet tuplet = TupletInteger(KEY_IMAGE_REQUEST_NEXT, 0);
  send_app_message(send_uint8, &tuplet);
}

static void update_lmst(uint32_t *ms) {
  static char lmst_string[20];
  getMarsTimeString(lmst_string, 20, getMslEpoch(), 0);
  text_layer_set_text(lmst_layer, lmst_string);
  app_timer_register(*ms, (AppTimerCallback) update_lmst, ms);
}

static void handle_new_position(AccelData *accel) {
  static char g_text[100];
  static int32_t angle;
  static uint32_t tilted = 0;

  angle = atan2_lookup(accel->y, accel->z);
  if (angle < 0) angle = 0;

  // Min tilt angle computed from atan of y and z axis.
  // When Pebble is flat, angle is 180 degrees.
  // When roated towards your face, angle increases.
  // Per atan2_lookup API: 0x10000 = 360 degrees
  // To achieve tilt between 50 and 90 degrees:
  //  Min = (0x10000 / 360) * (180+50) = 41860
  //  Max = (0x10000 / 360) * (180+90) = 49140

  if (angle > 41860 && angle < 49140) {
    snprintf(g_text, sizeof(g_text), "%s %d", "Tilted", (int)angle);
    if (tilted == 0) {
      //vibes_short_pulse();
    }
    tilted = 1;
  } else {
    snprintf(g_text, sizeof(g_text), "%d", (int)angle);
    if (tilted == 1) {
      //vibes_double_pulse();
    }
    tilted = 0;
  }

  //snprintf(g_text, sizeof(g_text), "%d %d %d", accel->x, accel->y, accel->z);
  //snprintf(g_text, sizeof(g_text), "%d", (int)angle);

  //APP_LOG(APP_LOG_LEVEL_DEBUG, "accel position: %d %d %d", accel->x, accel->y, accel->z);

  text_layer_set_text(lmst_layer, g_text);
  layer_mark_dirty(text_layer_get_layer(lmst_layer));

}

/*
static void timer_callback(void *data) {
  AccelData accel = (AccelData) { .x = 0, .y = 0, .z = 0 };

  accel_service_peek(&accel);
  handle_new_position(&accel);

  g_timer = app_timer_register(330, timer_callback, NULL);
}
static void handle_accel(AccelData *accel_data, uint32_t num_samples) {
  handle_new_position(accel_data);
}
*/

void handle_init(void) {
  ui_init();

  app_message_register_inbox_received(app_message_in_received);
  app_message_register_outbox_sent(app_message_out_sent);
  app_message_register_outbox_failed(app_message_out_failed);

  app_message_open(app_message_inbox_size_maximum(), app_message_outbox_size_maximum());
  //app_message_open(124, 124);

  accel_tap_service_subscribe(handle_accel_tap);

  hide_mars_time = (bool)persist_read_int(PERSIST_HIDE_MARS_TIME_KEY);

  update_mars_time_visibility();

  lmst_update_interval = 10274;
  update_lmst(&lmst_update_interval);

  // Tilt
  //accel_data_service_subscribe(15, handle_accel);
  //g_timer = app_timer_register(500 /* milliseconds */, timer_callback, NULL);

  if (DEBUG) APP_LOG(APP_LOG_LEVEL_DEBUG, "Application Started");
}

void handle_deinit(void) {
  ui_deinit();
  app_message_deregister_callbacks();
}

int main(void) {
  handle_init();
  app_event_loop();
  handle_deinit();
}
