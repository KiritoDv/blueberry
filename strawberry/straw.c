#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "straw.h"
#define MINIAUDIO_IMPLEMENTATION
#include "libs/miniaudio.h"

u8 is_paused = FALSE;
u8 is_running = FALSE;
char *file_path;
PyObject* callback = NULL;
ma_uint64 max_frames = 0;
ma_uint64 current_frames = 0;

ma_decoder decoder;
ma_device device;

static PyObject *get_max_frames(PyObject *self, PyObject *args, PyObject *kwargs){
    return Py_BuildValue("l", max_frames);
}

static PyObject *get_volume(PyObject *self, PyObject *args, PyObject *kwargs){
    float volume;

    ma_device_get_master_volume(&device, &volume);
    return Py_BuildValue("f", volume);
}

static PyObject *set_volume(PyObject *self, PyObject *args, PyObject *kwargs){
    float new_volume;

    static char *kwlist[] = {
        "status",
        NULL
    };

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "f", kwlist, &new_volume)) return NULL;
        
    ma_device_set_master_volume(&device, new_volume);

    return Py_None;
}

static PyObject *get_current_frames(PyObject *self, PyObject *args, PyObject *kwargs){
    return Py_BuildValue("l", current_frames);
}

static PyObject *running(PyObject *self, PyObject *args, PyObject *kwargs){    
    return Py_BuildValue("O", is_running ? Py_True : Py_False);
}

static PyObject *paused(PyObject *self, PyObject *args, PyObject *kwargs){    
    return Py_BuildValue("O", is_paused ? Py_True : Py_False);
}

static PyObject *close_player(PyObject *self, PyObject *args, PyObject *kwargs){
    if(&device != NULL && &decoder != NULL && is_running){
        ma_device_uninit(&device);
        ma_decoder_uninit(&decoder);
        is_running = FALSE;
    }    
    return Py_None;
}

static PyObject *set_play_status(PyObject *self, PyObject *args, PyObject *kwargs){
    
    PyObject *new_status;    

    static char *kwlist[] = {
        "status",
        NULL
    };

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O", kwlist, &new_status)) return NULL;
    
    is_paused = PyObject_IsTrue(new_status);
    return Py_None;
}

static void data_callback(ma_device* pDevice, void* pOutput, const void* pInput, ma_uint32 frameCount) {
    ma_decoder* pDecoder = (ma_decoder*)pDevice->pUserData;
    if (pDecoder == NULL) {
        return;
    }

    ma_decoder_get_available_frames(&decoder, &current_frames);
    if(current_frames <= 0) is_running = FALSE;

    if(is_paused) return;
    
    ma_decoder_read_pcm_frames(pDecoder, pOutput, frameCount);    

    (void)pInput;
}

static PyObject *load_player(PyObject *self, PyObject *args, PyObject *kwargs){
    ma_result result;
    static char *kwlist[] = {
        "path",
        "callback",
        NULL // DO NOT ;FORGET THIS AT THE END
    };

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "s|O", kwlist, &file_path, &callback))
        return NULL;

    result = ma_decoder_init_file(file_path, NULL, &decoder);
    if (result != MA_SUCCESS) {
        printf("Failed to load file\n");
        return Py_False;
    }

    max_frames = ma_decoder_get_length_in_pcm_frames(&decoder);
    return Py_True;
}

static PyObject *init_player(PyObject *self, PyObject *args, PyObject *kwargs){

    if(is_running)
        return Py_False;

    ma_device_config deviceConfig;    

    deviceConfig = ma_device_config_init(ma_device_type_playback);
    deviceConfig.playback.format   = decoder.outputFormat;
    deviceConfig.playback.channels = decoder.outputChannels;
    deviceConfig.sampleRate        = decoder.outputSampleRate;
    deviceConfig.dataCallback      = data_callback;
    deviceConfig.pUserData         = &decoder;    

    if (ma_device_init(NULL, &deviceConfig, &device) != MA_SUCCESS) {
        printf("Failed to open playback device.\n");
        ma_decoder_uninit(&decoder);
        return Py_False;
    }

    if (ma_device_start(&device) != MA_SUCCESS) {
        printf("Failed to start playback device.\n");
        ma_device_uninit(&device);
        ma_decoder_uninit(&decoder);
        return Py_False;
    }

    is_running = TRUE;

    if(callback != NULL && PyCallable_Check( callback )){
        Py_INCREF(callback);
    }

    return Py_True;
}

/* 
Define Methods.
We want our class to have callable methods (e.g Example.example_function()), so we define our methods
*/
static PyMethodDef miniaudio_methods[] = {
    {
        "load_player",
        load_player,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
    {
        "init_player",
        init_player,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
    {
        "get_max_frames",
        get_max_frames,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
    {
        "get_current_frames",
        get_current_frames,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
    {
        "running",
        running,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
    {
        "paused",
        paused,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
    {
        "close_player",
        close_player,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
    {
        "set_play_status",
        set_play_status,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
    {
        "set_volume",
        set_volume,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
    {
        "get_volume",
        get_volume,
        METH_VARARGS | METH_KEYWORDS,
        "Init miniaudio player"
    },
};

/* 
Define Module.
We want to define Example, so that we can call it.
*/
static struct PyModuleDef Strawberry_definition = {PyModuleDef_HEAD_INIT, "strawberry", "Strawberry player wrapper", -1, miniaudio_methods};

/* 
Initialize Module.
*/
PyMODINIT_FUNC
PyInit_strawberry(void) {
    if (! PyEval_ThreadsInitialized()) {
        PyEval_InitThreads();
    }
    return PyModule_Create(&Strawberry_definition);
}