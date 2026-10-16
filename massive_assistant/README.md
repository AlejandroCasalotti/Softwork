# Asistente Massive Connector · Odoo 19

Instalar en Odoo.sh o servidor propio con addons Python. No compatible con Odoo Online. Copiar `massive_assistant` al addons_path, actualizar lista de aplicaciones e instalar. Requiere `cryptography`, HTTPS y `web.base.url` raíz pública correcta.

El administrador asigna el grupo **Asistente Massive · Usuario** a cada empleado autorizado. Los administradores de Ajustes reciben el grupo inicialmente. El icono flotante aparece dentro de Odoo; no se instala una extensión del navegador.

Cada usuario crea SU propia clave API de Odoo y la ingresa una vez en el panel. Pulsar Conectar y abrir el enlace: el propietario/administrador de la empresa en Massive Connector autoriza la conexión, UID y herramientas. Volver a Odoo y pulsar Completar vinculación. Se verifica en Odoo que la clave corresponde al UID solicitado. Nunca se usa la clave compartida del administrador para ejecutar las consultas del empleado. En Odoo 16–18 la conexión debe tener seleccionada su versión; el login individual viaja cifrado junto a la clave vinculada.

La IA operativa debe estar activada en Massive Connector con la cuenta API de IA de la empresa y sus permisos. Este módulo es un cliente integrado del servicio y herramientas de Massive Connector; no instala un segundo servidor MCP ni incluye un modelo de IA. El MCP externo sigue disponible por separado.

Las consultas, archivos y propuestas usan el mismo motor que la extensión. Los cambios requieren revisar filas y confirmar; presupuestos se crean en borrador. La IA y la API de Odoo siguen respetando ACL, reglas de registros y empresas del usuario de la clave. No usar claves de otros usuarios. Los permisos pueden restringirse además en Massive Connector. El módulo no usa `sudo` para operaciones sobre datos de negocio: solo para su propio registro cifrado de vinculación.

No se almacenan conversaciones ni archivos en Odoo. Se guarda temporalmente una vinculación cifrada por usuario durante ocho horas. La clave pendiente se elimina después de vincular; Massive Connector conserva la clave individual cifrada mientras dura el acceso y la limpia con su tarea periódica al vencer/revocar. Los archivos/propuestas usan Redis cifrado, retención y límites de Massive Connector. La limpieza horaria de Odoo elimina las vinculaciones vencidas. El historial del chat solo vive en la ventana; cerrar/recargar lo borra.

Desconectar revoca el token remoto antes de borrar la vinculación local (si hay conectividad). También puede revocarse desde Massive Connector. Antes de desinstalar, desconectar usuarios o revocar sus accesos desde Massive Connector. No eliminar el adjunto privado de cifrado referenciado por `massive_assistant.key_attachment` mientras haya vinculaciones activas. Respaldar base y filestore juntos.

Los paquetes de 16–20 se generan desde una fuente común, con rutas JSON para 16–18 y JSON-RPC para 19–20. Las pruebas de contrato y DOM no sustituyen instalación y aceptación en cada versión y edición real. Verificar primero en una base de pruebas antes de producción o publicación en Odoo Apps.
