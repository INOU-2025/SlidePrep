# Manual técnico: sistema de configuración de SlidePrep

## Objetivo

Este documento explica, para programadores que se incorporan al proyecto, cómo funciona el sistema de configuración de SlidePrep, qué elementos componen una configuración válida y cómo crear una configuración nueva para producción o pruebas de pasos aislados.

---

## 1. Arquitectura del sistema de configuración

El sistema de configuración tiene cuatro capas principales:

1. **Esquema tipado (Pydantic)** en `config/config_schema.py`.
2. **Contrato agregado de aplicación** en `api/schemas.py` (`AppConfig`).
3. **Administrador de configuración** en `src/core/app_config_manager.py`.
4. **Bootstrap + DI container** en `src/core/bootstrap.py`.

### Flujo de inicialización

1. Se carga un archivo JSON de configuración.
2. `AppConfigManager` convierte cada sección a objetos tipados (`GeneralConfig`, `BinarizationConfig`, etc.).
3. Se aplican validaciones de campos y de modelo (paths, enums, rangos numéricos, etc.).
4. `bootstrap()` registra config, logger, debugger y contexto en el contenedor.
5. `PipelineService` crea los steps usando la configuración tipada de cada módulo.

Este diseño evita strings sueltos en el código de negocio y centraliza validación + defaults en un único lugar.

---

## 2. Elementos que integran una configuración

Una configuración completa está organizada por secciones JSON. No todas son obligatorias en todos los casos.

## 2.1 `general`

Controla parámetros globales:

- `input_path`: ruta de entrada (archivo o carpeta).
- `output_path`: ruta base de salida.
- `suffix_filter`: filtro por sufijo para lotes.
- `output_suffix`: sufijo para archivos procesados.
- `log`: habilita/deshabilita logging.
- `debug`: habilita/deshabilita artefactos de depuración.

## 2.2 `test` (opcional, para pruebas aisladas)

Permite ejecutar scripts de testing sin alterar `general`:

- `input_path`: ruta de datos de prueba.
- `output_path`: ruta de resultados de prueba.
- `input_type`: `"image"` o `"data"`.
- `max_images`: límite de archivos a procesar.

> Si `test.output_path` está definido, se usa como base para logs y debug en pruebas.

## 2.3 Secciones de steps

Cada step tiene su bloque independiente:

- `binarization`
- `grid_detection`
- `grid_refinement`
- `inpainting`
- `img_conversion`
- `stitching`

La regla de diseño es: **cada step solo consume su propia sección**.

## 2.4 `log`

Define destino y nivel de logging:

- `log_to_file`
- `log_to_console`
- `log_file_name`
- `log_level`
- `relative_path`

## 2.5 `debug`

Controla persistencia de artefactos de depuración:

- `saved_artifact_type`: `"image" | "data" | "both"`
- `save_composite_img`
- `save_aggregated_data`
- `input_result_file_name`
- `result_file_name`
- `relative_path`
- `artifact_sink`: `"local" | "memory"`

---

## 3. Validación y defaults

La validación ocurre al instanciar los modelos de Pydantic. Ejemplos de reglas:

- Paths de entrada/máscara/modelo deben existir cuando se informan.
- Campos tipo enum (formatos, niveles de log, `input_type`) solo aceptan valores permitidos.
- Rangos numéricos (`overlap`, thresholds, etc.) se validan explícitamente.

Si una sección opcional no está presente, el sistema puede:

- usar `None` para steps opcionales, o
- crear defaults seguros para ciertos bloques (por ejemplo, stitching).

---

## 4. Cómo crear una configuración nueva

## 4.1 Caso A: configuración de pipeline completo

1. Copiar `config/development.json` o `config/production.json`.
2. Ajustar `general.input_path` y `general.output_path`.
3. Completar parámetros de todos los steps del flujo que se vaya a ejecutar.
4. Ajustar políticas de `log` y `debug`.
5. Ejecutar el pipeline con `main.py`.

Ejemplo mínimo:

```json
{
  "general": {
    "input_path": "data/input",
    "output_path": "data/output",
    "suffix_filter": "_ch00",
    "output_suffix": "_processed",
    "log": true,
    "debug": false
  },
  "binarization": {
    "threshold_method": "combined_differential"
  },
  "img_conversion": {
    "format": "png",
    "mode": "RGB"
  },
  "log": {
    "log_to_file": true,
    "log_to_console": true,
    "log_file_name": "pipeline.log",
    "log_level": "INFO"
  },
  "debug": {
    "saved_artifact_type": "image",
    "save_composite_img": false,
    "save_aggregated_data": false,
    "artifact_sink": "local"
  }
}
```

## 4.2 Caso B: configuración para test de un step

1. Crear un archivo en `config/test/` (por ejemplo, `mi_step.json`).
2. Incluir `general` + `test`.
3. Incluir solo la sección del step que se quiere evaluar.
4. Activar `debug` y logging detallado.
5. Ejecutar el script de test correspondiente en `src/scripts/`.

Ejemplo mínimo para binarización:

```json
{
  "general": {
    "input_path": "data/raw",
    "output_path": "data/dev_out",
    "suffix_filter": "_raw",
    "output_suffix": "_bin",
    "log": true,
    "debug": true
  },
  "binarization": {
    "threshold_method": "combined_differential"
  },
  "test": {
    "input_path": "data/raw",
    "output_path": "data/test_out",
    "input_type": "image",
    "max_images": 20
  },
  "log": {
    "log_to_file": false,
    "log_to_console": true,
    "log_level": "DEBUG"
  },
  "debug": {
    "saved_artifact_type": "image",
    "save_composite_img": true,
    "save_aggregated_data": false,
    "artifact_sink": "local"
  }
}
```

---

## 5. Integración con `PipelineService` y steps

`PipelineService` construye la cadena de steps con configuración ya tipada por `AppConfigManager`. La secuencia actual es:

1. `BinarizationStep`
2. `GridDetectionStep`
3. `GridRefinementStep`
4. `MaskCreationStep`
5. `InpaintingStep`
6. `ImgConversionStep`

Para agregar un step nuevo:

1. Definir su clase de configuración en `config/config_schema.py`.
2. Exponerla en `api/schemas.py` (`AppConfig`).
3. Extraerla en `AppConfigManager`.
4. Inyectarla al construir el step en `PipelineService._create_pipeline()`.
5. Añadir documentación y configuración de ejemplo en `config/test/`.

---

## 6. Buenas prácticas recomendadas

- Mantener **nombres de secciones estables** para no romper scripts.
- Preferir defaults seguros en el esquema y validación estricta en runtime.
- Separar configuración de producción y test para evitar contaminación de artefactos.
- Versionar ejemplos de config en `config/test/` para facilitar reproducibilidad.
- Documentar cualquier campo nuevo en `docs/CONFIGURATION_GUIDE.md` y `docs/README.md`.

---

## 7. Lista de verificación rápida

Antes de ejecutar:

- [ ] `general.input_path` existe.
- [ ] `output_path` es escribible.
- [ ] Los enums (`log_level`, `input_type`, formatos) son válidos.
- [ ] Los paths de modelo/máscara existen si se declararon.
- [ ] La config de test usa `test.input_path` y `test.output_path` propios.
- [ ] `debug` y `log` están alineados con el objetivo (diagnóstico vs rendimiento).

Con este enfoque, la configuración en SlidePrep es modular, validable y extensible para pipeline completo o pruebas unitarias de cada paso.
