# Notas de Infraestructura - Casa Maravillas

## Problema Encontrado: Configuración de Correo Electrónico

### El Issue
- **Fecha**: 2026-06-10
- **Problema**: Los correos no se estaban enviando correctamente
- **Causa raíz**: La configuración del servidor de correo estaba apuntando a `casamaravillas.com` en lugar de `mail.casamaravillas.com`

### ¿Por qué ocurrió?
1. El dominio `casamaravillas.com` ahora apunta a **Shopify** (servidor externo con una IP completamente diferente)
2. Cuando la configuración de correo intentaba conectarse a `casamaravillas.com`, en realidad estaba intentando conectarse a **los servidores de Shopify**
3. Esto causaba que los intentos de envío de correos fallaran porque Shopify no tiene los servicios de correo configurados

### La Solución
Cambiar la configuración del servidor de correo para que apunte a:
```
mail.casamaravillas.com
```

En lugar de:
```
casamaravillas.com
```

### Dónde hacer los cambios
1. **En Plesk**:
   - Ve a **Correo** o **Mail**
   - Busca la configuración del dominio `casamaravillas.com`
   - Actualiza el MX Record (Mail eXchange) para que apunte a `mail.casamaravillas.com`

2. **En la configuración del sitio/aplicación** (si hay variables de entorno):
   - Busca cualquier variable que defina el servidor SMTP
   - Cambia de `casamaravillas.com` a `mail.casamaravillas.com`

### Arquitectura Actual
```
casamaravillas.com 
  ├─ DNS apunta a: Shopify (servidor externo)
  ├─ Contiene: E-commerce Shopify
  └─ NO contiene: Servidor de correo

mail.casamaravillas.com
  ├─ DNS apunta a: Plesk (servidor local)
  ├─ Contiene: Servidor de correo
  └─ Debe usarse para: Envío/recepción de emails

guia.casamaravillas.com
  ├─ DNS apunta a: Plesk (servidor local)
  ├─ Contiene: WordPress antiguo
  └─ URL archivada de referencia
```

### Próximos Pasos
1. Verificar la configuración de DNS para los MX Records
2. Actualizar cualquier aplicación que use SMTP
3. Probar el envío de correos después de los cambios
4. Esperar 24-48 horas para que la DNS se propague completamente

### Contacto
- Esta información debe ser revisada por: [Tu socio]
- Documentado por: Kiara
