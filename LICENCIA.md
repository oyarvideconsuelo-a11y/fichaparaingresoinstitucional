# LICENCIA DE USO Y DISTRIBUCIÓN
## Archivo Diseño Latinoamericano — Plataforma de Registro Institucional

---

**Titular:** [INSTITUCIÓN]  
**Año:** 2026  
**Versión:** 1.0  
**Base legal:** GNU Affero General Public License v3.0 (AGPL-3.0)  
**Idioma de referencia legal:** esta versión en español tiene igual validez que cualquier traducción oficial.

---

## 1. Objeto de esta licencia

Esta licencia regula el uso, copia, modificación y distribución del siguiente software, desarrollado en el marco del proyecto **Archivo Diseño Latinoamericano**:

- `app.py` — backend Flask (API REST, sistema de fichas institucionales)
- `form_institucional.html` — formulario público de ingreso de fichas
- `admin.html` — panel de administración interno
- Todo archivo de configuración, script o recurso que forme parte del mismo repositorio o paquete de distribución

No cubre los **datos del archivo** (fichas institucionales, imágenes cargadas por usuarios, base de datos `fichas.json`), que están sujetos a condiciones separadas de uso académico y privacidad.

---

## 2. Permisos otorgados

Bajo esta licencia, cualquier persona o institución tiene derecho a:

**a) Usar** el software para cualquier fin, incluyendo investigación, docencia, prototipos y servicios públicos, sin pago de regalías.

**b) Estudiar** el código fuente y comprender su funcionamiento.

**c) Copiar y distribuir** copias exactas del software, en cualquier medio, siempre que se incluya esta licencia completa y el aviso de copyright original.

**d) Modificar y distribuir versiones adaptadas**, siempre que se cumplan las condiciones del punto 3 (copyleft).

**e) Ejecutar el software como servicio en red** (servidor público, API web, aplicación SaaS), siempre que se cumplan las condiciones del punto 4 (cláusula de red).

---

## 3. Condiciones de copyleft (obras derivadas)

Toda obra derivada de este software — incluyendo modificaciones, ampliaciones, integraciones o traducciones — debe:

**3.1** Distribuirse bajo esta misma licencia (AGPL-3.0) o una versión posterior de la misma, sin restricciones adicionales.

**3.2** Incluir el código fuente completo de la obra derivada, accesible de forma pública o bajo solicitud, sin costo.

**3.3** Conservar de forma visible el aviso de copyright original:

> *Software desarrollado por [INSTITUCIÓN] (2026) en el marco del Archivo Diseño Latinoamericano. Distribuido bajo AGPL-3.0.*

**3.4** Documentar claramente qué partes fueron modificadas respecto al original, con fecha de modificación.

**3.5** No aplicar medidas técnicas (DRM, ofuscación, compilación sin fuente) que impidan a terceros ejercer los derechos de esta licencia sobre la obra derivada.

---

## 4. Cláusula de red (uso como servicio)

Esta cláusula es específica de la AGPL y distingue esta licencia de la GPL estándar.

Si ejecutás este software en un servidor accesible por terceros a través de una red (internet, intranet, servicio web, API pública), **tenés la obligación de ofrecer el código fuente completo** de la versión que estás ejecutando a todos los usuarios que interactúen con ese servicio.

Esto significa que:

- Debe existir un enlace visible en la interfaz del servicio que permita descargar o acceder al código fuente.
- El código ofrecido debe corresponder exactamente a la versión en producción, incluyendo cualquier modificación.
- No es suficiente enlazar al repositorio original si la versión en producción fue modificada.

---

## 5. Atribución requerida

Todo uso público del software — ya sea como servicio, en publicaciones académicas, en materiales docentes o en repositorios — debe incluir la siguiente atribución:

> **Archivo Diseño Latinoamericano — Plataforma de Registro Institucional**  
> Desarrollado por [INSTITUCIÓN], 2026.  
> Código fuente disponible bajo AGPL-3.0.  
> [URL del repositorio]

En publicaciones académicas se recomienda citar como:

> [INSTITUCIÓN] (2026). *Archivo Diseño Latinoamericano: plataforma de registro institucional* [software]. Distribuido bajo GNU AGPL v3.0. Recuperado de [URL].

---

## 6. Usos no permitidos

Sin perjuicio de los permisos otorgados, esta licencia **no autoriza**:

**6.1 Uso comercial cerrado:** incorporar este software en un producto comercial de código cerrado sin liberar el código modificado bajo AGPL-3.0.

**6.2 Eliminación de atribución:** suprimir, ocultar o modificar los avisos de copyright y atribución institucional.

**6.3 Uso engañoso:** utilizar el nombre, logo o identidad de [INSTITUCIÓN] para respaldar productos derivados sin autorización expresa por escrito.

**6.4 Restricción de derechos de terceros:** imponer a los usuarios del software restricciones que les impidan ejercer los derechos que esta licencia les otorga.

---

## 7. Privacidad y datos de usuarios externos

El software incluye mecanismos de protección de datos (rate limiting por hash, tokens CSRF, sanitización de inputs, eliminación de metadatos EXIF). Quien despliegue este software asume la responsabilidad de:

- Mantener o mejorar dichos mecanismos, sin debilitarlos.
- Cumplir con la legislación de protección de datos aplicable en su jurisdicción.
- No modificar el software para recolectar datos personales de los usuarios del formulario (nombre, email, IP, localización) sin consentimiento explícito e informado.

[INSTITUCIÓN] no asume responsabilidad por implementaciones del software realizadas por terceros que vulneren la privacidad de los usuarios.

---

## 8. Ausencia de garantía

Este software se distribuye **sin garantía de ningún tipo**, expresa o implícita, incluyendo pero no limitándose a garantías de comerciabilidad, idoneidad para un fin particular o no infracción.

[INSTITUCIÓN] no asume responsabilidad por daños directos, indirectos, incidentales o consecuentes derivados del uso o la imposibilidad de uso del software.

---

## 9. Terminación

Los derechos otorgados bajo esta licencia se terminan automáticamente si:

- Se incumplen las condiciones de copyleft (punto 3).
- Se viola la cláusula de red (punto 4).
- Se eliminan atribuciones requeridas (punto 6.2).

La terminación no afecta los derechos de terceros que hayan recibido copias o licencias del software antes de la violación, siempre que ellos cumplan con sus propias obligaciones.

---

## 10. Versiones futuras de esta licencia

[INSTITUCIÓN] puede publicar versiones revisadas de esta licencia. Cada versión tendrá un número de versión distintivo. Si el software especifica una versión concreta de esta licencia, se aplica esa versión. Si no especifica versión, se puede aplicar cualquier versión publicada por la Free Software Foundation.

---

## 11. Ley aplicable

Esta licencia se interpreta de acuerdo con los principios generales del derecho internacional aplicables a licencias de software libre, y en particular con los términos de la GNU AGPL v3.0 publicada por la Free Software Foundation (https://www.gnu.org/licenses/agpl-3.0.html).

En caso de conflicto entre esta adaptación en español y el texto oficial en inglés de la AGPL-3.0, prevalece el texto oficial en inglés en lo relativo a los permisos y obligaciones de la licencia base. Las cláusulas adicionales (puntos 7 y 6.3) son complementarias y se rigen por la jurisdicción de [PAÍS/PROVINCIA donde está radicada la INSTITUCIÓN].

---

## Aviso de copyright

```
Copyright (C) 2026  [INSTITUCIÓN]

Este programa es software libre: podés redistribuirlo y/o modificarlo
bajo los términos de la GNU Affero General Public License publicada por
la Free Software Foundation, ya sea la versión 3 de la Licencia, o
(a tu elección) cualquier versión posterior.

Este programa se distribuye con la esperanza de que sea útil,
pero SIN NINGUNA GARANTÍA; sin siquiera la garantía implícita de
COMERCIABILIDAD o IDONEIDAD PARA UN PROPÓSITO PARTICULAR.
Ver la GNU Affero General Public License para más detalles.

Debés haber recibido una copia de la GNU Affero General Public License
junto con este programa. Si no, consultá <https://www.gnu.org/licenses/>.
```

---

## Resumen no vinculante (plain language)

| Acción | ¿Permitido? |
|--------|------------|
| Usar el software para investigación o docencia | ✓ Sí |
| Modificar el código para tu institución | ✓ Sí, publicando el código modificado |
| Desplegarlo como servicio web público | ✓ Sí, ofreciendo el código fuente a los usuarios |
| Redistribuir copias | ✓ Sí, con esta misma licencia |
| Incorporarlo en software comercial cerrado | ✗ No |
| Quitar la atribución a [INSTITUCIÓN] | ✗ No |
| Usarlo sin publicar las modificaciones | ✗ No |
| Agregar restricciones adicionales a los usuarios | ✗ No |

*Este resumen es orientativo. En caso de duda, prevalece el texto completo de la licencia.*

---

*Licencia generada en el marco del proyecto Archivo Diseño Latinoamericano · 2026*
