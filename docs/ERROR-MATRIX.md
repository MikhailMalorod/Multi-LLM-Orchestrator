# 📊 МАТРИЦА ВАЛИДАЦИИ API КЛЮЧЕЙ: СЦЕНАРИИ И СООБЩЕНИЯ

**Версия**: 1.0.0
**Дата**: 09.01.2026
**Стиль**: semantic_core_ru_v1.1.md (формальный, data-driven, action-oriented)

***

## ЛЕГЕНДА ТИПОВ ОШИБОК

| Код | Тип ошибки | HTTP | Описание |
| :-- | :-- | :-- | :-- |
| **E1** | `invalid_api_key` | 401 | Ключ недействителен или истёк |
| **E2** | `scope_mismatch` | 400 | Ключ не соответствует версии API (GigaChat) |
| **E3** | `permission_denied` | 403 | Нет доступа к folder_id (YandexGPT) |
| **E4** | `rate_limit_exceeded` | 429 | Превышен лимит запросов |
| **E5** | `network_timeout` | 504 | Timeout (сетевые проблемы) |
| **E6** | `provider_error` | 500 | Внутренняя ошибка провайдера |
| **S1** | `success` | 200 | Ключ действителен |


***

## СЦЕНАРИЙ 1: АДМИН ДОБАВЛЯЕТ КЛЮЧ GIGACHAT

**Контекст**: Admin Panel → Platform API Keys → Add Key → Provider: GigaChat
**UI компоненты**: Modal dialog, Input (API key), Button (Validate \& Detect Type), Alert, Toast

***

### E1: Invalid API Key (401)

**Триггер**: GigaChat API возвращает 401 Unauthorized

**Действия системы:**

1. Показать Alert (destructive) в модальном окне
2. Сохранить фокус на поле API Key
3. Не закрывать модальное окно
4. Записать в audit log: `action: "validation_failed", reason: "invalid_api_key"`

**UI компоненты:**

```tsx
// Alert (destructive)
<Alert variant="destructive">
  <XCircle className="h-4 w-4" />
  <AlertTitle>Ключ GigaChat недействителен</AlertTitle>
  <AlertDescription>
    API ключ не прошёл проверку. Ключ может быть истёкшим или удалённым.
    <div className="mt-2 text-sm">
      <strong>Что делать:</strong>
      <ol className="list-decimal ml-4 mt-1">
        <li>Проверьте, скопирован ли ключ полностью</li>
        <li>Перевыпустите ключ в <Link href="https://developers.sber.ru/studio">личном кабинете Studio</Link></li>
      </ol>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Ключ GigaChat недействителен"
- **Описание**: "API ключ не прошёл проверку. Ключ может быть истёкшим или удалённым."
- **Действие**: "Проверьте, скопирован ли ключ полностью. Перевыпустите ключ в личном кабинете Studio."
- **Help link**: https://developers.sber.ru/studio

***

### E2: Scope Mismatch (400, code: 7)

**Триггер**: GigaChat API возвращает 400 (code: 7, "scope mismatch")

**Действия системы:**

1. Показать Alert (warning) с детектированным scope
2. Предложить исправить scope автоматически
3. Записать в audit log: `action: "validation_failed", reason: "scope_mismatch", detected_scope: "GIGACHAT_API_B2B"`

**UI компоненты:**

```tsx
// Alert (warning)
<Alert variant="warning">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>Ключ не соответствует версии API</AlertTitle>
  <AlertDescription>
    Обнаружен конфликт между ключом и версией API. Ключ относится к типу <strong>GIGACHAT_API_B2B</strong>.
    <div className="mt-3">
      <Button variant="default" onClick={autoFixScope}>
        Использовать тип GIGACHAT_API_B2B
      </Button>
      <Button variant="outline" className="ml-2" onClick={retryManual}>
        Изменить ключ вручную
      </Button>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Ключ не соответствует версии API"
- **Описание**: "Обнаружен конфликт между ключом и версией API. Ключ относится к типу GIGACHAT_API_B2B."
- **Действие**: "Использовать тип GIGACHAT_API_B2B (автоматически) или изменить ключ вручную."

***

### E3: N/A для GigaChat

_(Permission denied не применим к GigaChat — только для YandexGPT)_

***

### E4: Rate Limit Exceeded (429)

**Триггер**: GigaChat API возвращает 429 Too Many Requests

**Действия системы:**

1. Показать Alert (info) с таймером
2. Автоматический retry через 30 секунд
3. Disable кнопку "Validate" на 30 секунд
4. Записать в audit log: `action: "validation_failed", reason: "rate_limit_exceeded"`

**UI компоненты:**

```tsx
// Alert (info) with countdown timer
<Alert variant="info">
  <Clock className="h-4 w-4" />
  <AlertTitle>Превышен лимит запросов</AlertTitle>
  <AlertDescription>
    GigaChat API ограничивает количество одновременных запросов (1 запрос в секунду для физических лиц).
    <div className="mt-2 flex items-center gap-2">
      <span className="text-sm">Повторная проверка через</span>
      <Badge variant="secondary">{countdown} сек</Badge>
    </div>
    <Button 
      variant="outline" 
      className="mt-3" 
      onClick={retryNow} 
      disabled={countdown > 0}
    >
      {countdown > 0 ? `Подождите ${countdown} сек` : "Повторить проверку"}
    </Button>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Превышен лимит запросов"
- **Описание**: "GigaChat API ограничивает количество одновременных запросов (1 запрос в секунду для физических лиц)."
- **Действие**: "Повторная проверка через [countdown] секунд." (автоматический retry)

***

### E5: Network Timeout (504)

**Триггер**: httpx.TimeoutException (>10 секунд)

**Действия системы:**

1. Показать Alert (warning)
2. Предложить retry (без автоматической попытки)
3. Записать в audit log: `action: "validation_failed", reason: "network_timeout"`

**UI компоненты:**

```tsx
// Alert (warning)
<Alert variant="warning">
  <Wifi className="h-4 w-4" />
  <AlertTitle>Не удалось связаться с GigaChat API</AlertTitle>
  <AlertDescription>
    Превышено время ожидания ответа (10 секунд). Возможны проблемы с сетью или временная недоступность сервиса.
    <div className="mt-3">
      <Button variant="default" onClick={retry}>
        Повторить попытку
      </Button>
      <Button variant="outline" className="ml-2" onClick={cancel}>
        Отменить
      </Button>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Не удалось связаться с GigaChat API"
- **Описание**: "Превышено время ожидания ответа (10 секунд). Возможны проблемы с сетью или временная недоступность сервиса."
- **Действие**: "Повторить попытку или отменить."

***

### E6: Provider Server Error (500)

**Триггер**: GigaChat API возвращает 500 Internal Server Error

**Действия системы:**

1. Показать Alert (destructive)
2. Записать в audit log + error log: `action: "validation_failed", reason: "provider_error", status_code: 500`
3. Показать Error ID для support

**UI компоненты:**

```tsx
// Alert (destructive)
<Alert variant="destructive">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Внутренняя ошибка GigaChat API</AlertTitle>
  <AlertDescription>
    Сервис GigaChat временно недоступен (ошибка 500). Данные о проблеме переданы в поддержку.
    <div className="mt-2 text-xs text-muted-foreground font-mono">
      Error ID: {errorId}
    </div>
    <div className="mt-3">
      <Button variant="outline" onClick={retry}>
        Повторить позже
      </Button>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Внутренняя ошибка GigaChat API"
- **Описание**: "Сервис GigaChat временно недоступен (ошибка 500). Данные о проблеме переданы в поддержку."
- **Действие**: "Повторить позже."
- **Error ID**: `err_{timestamp}_{random}`

***

### S1: Success (200)

**Триггер**: GigaChat API возвращает 200 OK, scope определён

**Действия системы:**

1. Показать Alert (success) с детектированным scope
2. Auto-fill поле Scope (read-only)
3. Enable кнопку "Add Key"
4. Записать в audit log: `action: "validation_success", provider: "gigachat", detected_scope: "GIGACHAT_API_B2B"`

**UI компоненты:**

```tsx
// Alert (success)
<Alert variant="success">
  <CheckCircle className="h-4 w-4" />
  <AlertTitle>Ключ GigaChat действителен</AlertTitle>
  <AlertDescription>
    Тип ключа: <strong>GIGACHAT_API_B2B</strong> (юридические лица, корпоративные клиенты)
    <div className="mt-2 text-sm text-muted-foreground">
      Ключ прошёл проверку и готов к добавлению.
    </div>
  </AlertDescription>
</Alert>

// Read-only field (auto-filled)
<FormField name="scope">
  <FormLabel>Тип ключа (определён автоматически)</FormLabel>
  <FormControl>
    <Input value="GIGACHAT_API_B2B" disabled />
  </FormControl>
  <FormDescription>
    Тип определён автоматически при проверке ключа.
  </FormDescription>
</FormField>
```

**Текст сообщения:**

- **Заголовок**: "Ключ GigaChat действителен"
- **Описание**: "Тип ключа: GIGACHAT_API_B2B (юридические лица, корпоративные клиенты). Ключ прошёл проверку и готов к добавлению."

**Toast (после добавления ключа):**

```tsx
toast({
  title: "Ключ добавлен",
  description: "Platform API key gc-prod-001 добавлен. Квота: 50,000,000 токенов.",
  variant: "default",
});
```


***

## СЦЕНАРИЙ 2: АДМИН ДОБАВЛЯЕТ КЛЮЧ YANDEXGPT

**Контекст**: Admin Panel → Platform API Keys → Add Key → Provider: YandexGPT
**UI компоненты**: Modal dialog, Input (API key), Input (Folder ID), Button (Validate), Alert, Toast

***

### E1: Invalid API Key (401)

**Триггер**: YandexGPT API возвращает 401 UNAUTHENTICATED

**Действия системы:**

1. Показать Alert (destructive) в модальном окне
2. Сохранить фокус на поле API Key
3. Записать в audit log: `action: "validation_failed", reason: "invalid_api_key"`

**UI компоненты:**

```tsx
// Alert (destructive)
<Alert variant="destructive">
  <XCircle className="h-4 w-4" />
  <AlertTitle>Ключ YandexGPT недействителен</AlertTitle>
  <AlertDescription>
    API ключ не прошёл проверку (ошибка 401). Ключ может быть неверным или удалённым.
    <div className="mt-2 text-sm">
      <strong>Что делать:</strong>
      <ol className="list-decimal ml-4 mt-1">
        <li>Проверьте формат ключа (начинается с "AQVN...")</li>
        <li>Перевыпустите ключ в <Link href="https://console.cloud.yandex.ru">Yandex Cloud Console</Link></li>
      </ol>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Ключ YandexGPT недействителен"
- **Описание**: "API ключ не прошёл проверку (ошибка 401). Ключ может быть неверным или удалённым."
- **Действие**: "Проверьте формат ключа (начинается с 'AQVN...'). Перевыпустите ключ в Yandex Cloud Console."
- **Help link**: https://console.cloud.yandex.ru

***

### E2: N/A для YandexGPT

_(Scope mismatch не применим к YandexGPT — только для GigaChat)_

***

### E3: Permission Denied (403)

**Триггер**: YandexGPT API возвращает 403 PERMISSION_DENIED

**Действия системы:**

1. Показать Alert (warning) с детальным объяснением
2. Highlight поле Folder ID (красная рамка)
3. Записать в audit log: `action: "validation_failed", reason: "permission_denied", folder_id: "b1g..."`

**UI компоненты:**

```tsx
// Alert (warning)
<Alert variant="warning">
  <ShieldAlert className="h-4 w-4" />
  <AlertTitle>Нет доступа к YandexGPT API</AlertTitle>
  <AlertDescription>
    API ключ не имеет прав доступа к folder_id <code className="text-xs bg-muted px-1 py-0.5 rounded">{folderId}</code>.
    <div className="mt-2 text-sm">
      <strong>Что делать:</strong>
      <ol className="list-decimal ml-4 mt-1">
        <li>Убедитесь, что сервисный аккаунт имеет роль <code className="bg-muted px-1 py-0.5 rounded text-xs">ai.languageModels.user</code></li>
        <li>Проверьте, что folder_id указан верно (скопируйте из Yandex Cloud Console)</li>
        <li>Подождите 1-2 минуты после назначения роли (IAM синхронизация)</li>
      </ol>
    </div>
    <Button variant="outline" className="mt-3" onClick={() => window.open("https://yandex.cloud/ru/docs/iam/operations/sa/assign-role-for-sa")}>
      Инструкция по назначению роли
    </Button>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Нет доступа к YandexGPT API"
- **Описание**: "API ключ не имеет прав доступа к folder_id [ID]. Убедитесь, что сервисный аккаунт имеет роль ai.languageModels.user."
- **Действие**: "Назначьте роль в Yandex Cloud IAM. Инструкция по ссылке."
- **Help link**: https://yandex.cloud/ru/docs/iam/operations/sa/assign-role-for-sa

***

### E4: Rate Limit Exceeded (429)

**Триггер**: YandexGPT API возвращает 429 RESOURCE_EXHAUSTED

**Действия системы:**

1. Показать Alert (info) с countdown
2. Автоматический retry через 10 секунд
3. Записать в audit log: `action: "validation_failed", reason: "rate_limit_exceeded"`

**UI компоненты:**

```tsx
// Alert (info) with countdown
<Alert variant="info">
  <Clock className="h-4 w-4" />
  <AlertTitle>Превышен лимит запросов</AlertTitle>
  <AlertDescription>
    YandexGPT API ограничивает количество запросов в секунду.
    <div className="mt-2 flex items-center gap-2">
      <span className="text-sm">Повторная проверка через</span>
      <Badge variant="secondary">{countdown} сек</Badge>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Превышен лимит запросов"
- **Описание**: "YandexGPT API ограничивает количество запросов в секунду."
- **Действие**: "Повторная проверка через [countdown] секунд." (автоматический retry)

***

### E5: Network Timeout (504)

**Триггер**: httpx.TimeoutException (>10 секунд)

**Действия системы:**

1. Показать Alert (warning)
2. Предложить retry (без автоматической попытки)
3. Записать в audit log: `action: "validation_failed", reason: "network_timeout"`

**UI компоненты:**

```tsx
// Alert (warning)
<Alert variant="warning">
  <Wifi className="h-4 w-4" />
  <AlertTitle>Не удалось связаться с YandexGPT API</AlertTitle>
  <AlertDescription>
    Превышено время ожидания ответа (10 секунд). Возможны проблемы с сетью или временная недоступность сервиса.
    <div className="mt-3">
      <Button variant="default" onClick={retry}>
        Повторить попытку
      </Button>
      <Button variant="outline" className="ml-2" onClick={cancel}>
        Отменить
      </Button>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Не удалось связаться с YandexGPT API"
- **Описание**: "Превышено время ожидания ответа (10 секунд). Возможны проблемы с сетью или временная недоступность сервиса."
- **Действие**: "Повторить попытку или отменить."

***

### E6: Provider Server Error (500)

**Триггер**: YandexGPT API возвращает 500 INTERNAL

**Действия системы:**

1. Показать Alert (destructive)
2. Записать в audit log + error log
3. Показать Request ID (из google.rpc.RequestInfo)

**UI компоненты:**

```tsx
// Alert (destructive)
<Alert variant="destructive">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Внутренняя ошибка YandexGPT API</AlertTitle>
  <AlertDescription>
    Сервис YandexGPT временно недоступен (ошибка 500). Данные о проблеме переданы в поддержку.
    <div className="mt-2 text-xs text-muted-foreground font-mono">
      Request ID: {requestId}
    </div>
    <div className="mt-3">
      <Button variant="outline" onClick={retry}>
        Повторить позже
      </Button>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Внутренняя ошибка YandexGPT API"
- **Описание**: "Сервис YandexGPT временно недоступен (ошибка 500). Данные о проблеме переданы в поддержку."
- **Действие**: "Повторить позже."
- **Request ID**: из response (google.rpc.RequestInfo)

***

### S1: Success (200)

**Триггер**: YandexGPT API возвращает 200 OK

**Действия системы:**

1. Показать Alert (success)
2. Enable кнопку "Add Key"
3. Записать в audit log: `action: "validation_success", provider: "yandexgpt", folder_id: "b1g..."`

**UI компоненты:**

```tsx
// Alert (success)
<Alert variant="success">
  <CheckCircle className="h-4 w-4" />
  <AlertTitle>Ключ YandexGPT действителен</AlertTitle>
  <AlertDescription>
    API ключ имеет доступ к folder_id <code className="text-xs bg-green-100 px-1 py-0.5 rounded">{folderId}</code>.
    <div className="mt-2 text-sm text-muted-foreground">
      Ключ прошёл проверку и готов к добавлению.
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Ключ YandexGPT действителен"
- **Описание**: "API ключ имеет доступ к folder_id [ID]. Ключ прошёл проверку и готов к добавлению."

**Toast (после добавления ключа):**

```tsx
toast({
  title: "Ключ добавлен",
  description: "Platform API key yc-prod-002 добавлен. Квота: 50,000,000 токенов.",
  variant: "default",
});
```


***

## СЦЕНАРИЙ 3: ПОЛЬЗОВАТЕЛЬ ДОБАВЛЯЕТ КЛЮЧ GIGACHAT (BYOK)

**Контекст**: User Dashboard → Settings → API Keys → Add Your Key → Provider: GigaChat
**UI компоненты**: Form, Input (API key), Button (Validate \& Upgrade to BYOK), Alert, Toast, Confirmation dialog

***

### E1: Invalid API Key (401)

**Триггер**: GigaChat API возвращает 401 Unauthorized

**Действия системы:**

1. Показать Alert (destructive) inline (под полем ввода)
2. Сохранить фокус на поле API Key
3. НЕ создавать subscription
4. Записать в audit log: `action: "byok_validation_failed", reason: "invalid_api_key", tenant_id: "..."`

**UI компоненты:**

```tsx
// Alert (destructive) inline
<Alert variant="destructive" className="mt-3">
  <XCircle className="h-4 w-4" />
  <AlertTitle>Ключ GigaChat не прошёл проверку</AlertTitle>
  <AlertDescription>
    API ключ недействителен или истёк. Переход на BYOK Starter невозможен.
    <div className="mt-2 text-sm">
      <strong>Что делать:</strong>
      <ol className="list-decimal ml-4 mt-1">
        <li>Убедитесь, что ключ скопирован полностью (без пробелов)</li>
        <li>Перевыпустите ключ в <Link href="https://developers.sber.ru/studio" className="underline">личном кабинете GigaChat</Link></li>
        <li>Используйте ключ для физических лиц (GIGACHAT_API_PERS) или юридических лиц (GIGACHAT_API_B2B)</li>
      </ol>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Ключ GigaChat не прошёл проверку"
- **Описание**: "API ключ недействителен или истёк. Переход на BYOK Starter невозможен."
- **Действие**: "Убедитесь, что ключ скопирован полностью. Перевыпустите ключ в личном кабинете GigaChat."
- **Help link**: https://developers.sber.ru/studio

***

### E2: Scope Mismatch (400, code: 7)

**Триггер**: GigaChat API возвращает 400 (code: 7, "scope mismatch")

**Действия системы:**

1. Показать Alert (info) с детектированным scope
2. Автоматически использовать правильный scope
3. Продолжить миграцию с правильным scope
4. Записать в audit log: `action: "byok_validation_warning", reason: "scope_auto_fixed", detected_scope: "GIGACHAT_API_B2B"`

**UI компоненты:**

```tsx
// Alert (info)
<Alert variant="info" className="mt-3">
  <Info className="h-4 w-4" />
  <AlertTitle>Тип ключа определён автоматически</AlertTitle>
  <AlertDescription>
    Ваш ключ относится к типу <strong>GIGACHAT_API_B2B</strong> (юридические лица). 
    Тип определён автоматически и будет использован для настройки.
    <div className="mt-2 text-sm text-muted-foreground">
      Квота BYOK Starter: 10,000 запросов в месяц (в 10 раз больше Managed Starter).
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Тип ключа определён автоматически"
- **Описание**: "Ваш ключ относится к типу GIGACHAT_API_B2B (юридические лица). Тип определён автоматически и будет использован для настройки."
- **Действие**: (Автоматически продолжить миграцию)

***

### E3: N/A для GigaChat

_(Permission denied не применим к GigaChat)_

***

### E4: Rate Limit Exceeded (429)

**Триггер**: GigaChat API возвращает 429 Too Many Requests

**Действия системы:**

1. Показать Alert (warning) с countdown
2. Disable кнопку "Upgrade to BYOK" на 30 секунд
3. Автоматический retry через 30 секунд
4. Записать в audit log: `action: "byok_validation_failed", reason: "rate_limit_exceeded"`

**UI компоненты:**

```tsx
// Alert (warning) with countdown
<Alert variant="warning" className="mt-3">
  <Clock className="h-4 w-4" />
  <AlertTitle>Превышен лимит запросов GigaChat API</AlertTitle>
  <AlertDescription>
    Вы отправили слишком много запросов за короткое время. GigaChat ограничивает до 1 запроса в секунду для физических лиц.
    <div className="mt-2 flex items-center gap-2">
      <span className="text-sm">Повторная попытка через</span>
      <Badge variant="secondary" className="tabular-nums">{countdown} сек</Badge>
    </div>
    <Progress value={(30 - countdown) / 30 * 100} className="mt-2" />
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Превышен лимит запросов GigaChat API"
- **Описание**: "Вы отправили слишком много запросов за короткое время. GigaChat ограничивает до 1 запроса в секунду для физических лиц."
- **Действие**: "Повторная попытка через [countdown] секунд." (автоматически)

***

### E5: Network Timeout (504)

**Триггер**: httpx.TimeoutException (>10 секунд)

**Действия системы:**

1. Показать Alert (warning)
2. Предложить retry
3. НЕ создавать subscription
4. Записать в audit log: `action: "byok_validation_failed", reason: "network_timeout"`

**UI компоненты:**

```tsx
// Alert (warning)
<Alert variant="warning" className="mt-3">
  <Wifi className="h-4 w-4" />
  <AlertTitle>Не удалось проверить ключ</AlertTitle>
  <AlertDescription>
    Превышено время ожидания ответа от GigaChat API (10 секунд). Возможны проблемы с интернет-соединением.
    <div className="mt-3 flex gap-2">
      <Button variant="default" size="sm" onClick={retry}>
        Повторить попытку
      </Button>
      <Button variant="outline" size="sm" onClick={cancel}>
        Отменить
      </Button>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Не удалось проверить ключ"
- **Описание**: "Превышено время ожидания ответа от GigaChat API (10 секунд). Возможны проблемы с интернет-соединением."
- **Действие**: "Повторить попытку или отменить."

***

### E6: Provider Server Error (500)

**Триггер**: GigaChat API возвращает 500 Internal Server Error

**Действия системы:**

1. Показать Alert (destructive)
2. НЕ создавать subscription
3. Записать в audit log + error log
4. Показать Error ID

**UI компоненты:**

```tsx
// Alert (destructive)
<Alert variant="destructive" className="mt-3">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Ошибка сервиса GigaChat</AlertTitle>
  <AlertDescription>
    GigaChat API временно недоступен (ошибка 500). Переход на BYOK Starter отложен до восстановления сервиса.
    <div className="mt-2 text-xs text-muted-foreground font-mono">
      Error ID: {errorId}
    </div>
    <div className="mt-2 text-sm">
      Ваша подписка Managed Starter остаётся активной. Попробуйте повторить миграцию позже.
    </div>
    <Button variant="outline" size="sm" className="mt-3" onClick={close}>
      Понятно
    </Button>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Ошибка сервиса GigaChat"
- **Описание**: "GigaChat API временно недоступен (ошибка 500). Переход на BYOK Starter отложен до восстановления сервиса."
- **Действие**: "Ваша подписка Managed Starter остаётся активной. Попробуйте повторить миграцию позже."
- **Error ID**: `err_{timestamp}_{random}`

***

### S1: Success (200) → Upgrade Confirmation

**Триггер**: GigaChat API возвращает 200 OK, scope определён

**Действия системы:**

1. Показать Alert (success) с детектированным scope
2. Показать Confirmation Dialog с деталями миграции
3. Записать в audit log: `action: "byok_validation_success", provider: "gigachat", detected_scope: "..."`

**UI компоненты:**

```tsx
// Step 1: Alert (success) after validation
<Alert variant="success" className="mt-3">
  <CheckCircle className="h-4 w-4" />
  <AlertTitle>Ключ GigaChat действителен</AlertTitle>
  <AlertDescription>
    Тип ключа: <strong>GIGACHAT_API_B2B</strong>. Ключ готов к использованию.
    <div className="mt-2 text-sm text-muted-foreground">
      Квота BYOK Starter: 10,000 запросов в месяц (в 10 раз больше текущей).
    </div>
  </AlertDescription>
</Alert>

// Step 2: Confirmation Dialog
<Dialog open={showConfirmation}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Подтвердите переход на BYOK Starter</DialogTitle>
      <DialogDescription>
        Ваша подписка будет обновлена. Данные о миграции:
      </DialogDescription>
    </DialogHeader>
    
    <div className="space-y-4 py-4">
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="text-muted-foreground">Текущий тариф:</div>
        <div className="font-medium">Managed Starter (1,990 ₽/мес)</div>
        
        <div className="text-muted-foreground">Новый тариф:</div>
        <div className="font-medium">BYOK Starter (2,990 ₽/мес)</div>
        
        <div className="text-muted-foreground">Разница:</div>
        <div className="font-medium text-orange-600">+1,000 ₽/мес</div>
        
        <div className="text-muted-foreground">Квота:</div>
        <div className="font-medium">10,000 запросов/мес (×10)</div>
        
        <div className="text-muted-foreground">Тип ключа:</div>
        <div className="font-mono text-xs bg-muted px-2 py-1 rounded">GIGACHAT_API_B2B</div>
        
        <div className="text-muted-foreground">Downtime:</div>
        <div className="font-medium">~5 секунд (перезапуск бота)</div>
      </div>
      
      <Separator />
      
      <Alert variant="info">
        <Info className="h-4 w-4" />
        <AlertDescription className="text-sm">
          Следующий платёж будет списан по новому тарифу через {daysUntilBilling} дней 
          (<strong>{nextBillingDate}</strong>). Ваш ключ будет зашифрован и сохранён.
        </AlertDescription>
      </Alert>
    </div>
    
    <DialogFooter>
      <Button variant="outline" onClick={cancel}>
        Отменить
      </Button>
      <Button variant="default" onClick={confirmUpgrade} loading={isUpgrading}>
        {isUpgrading ? "Обновление..." : "Подтвердить и перейти на BYOK"}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>

// Step 3: Toast (after successful migration)
toast({
  title: "Переход на BYOK Starter выполнен",
  description: "Ваш ключ настроен. Квота: 10,000 запросов/мес. Следующий платёж: 2,990 ₽ через 28 дней.",
  variant: "default",
  duration: 7000,
});
```

**Текст сообщения:**

- **Alert Title**: "Ключ GigaChat действителен"
- **Alert Description**: "Тип ключа: GIGACHAT_API_B2B. Ключ готов к использованию. Квота BYOK Starter: 10,000 запросов в месяц (в 10 раз больше текущей)."
- **Dialog Title**: "Подтвердите переход на BYOK Starter"
- **Dialog Description**: Таблица с деталями миграции (тариф, цена, квота, downtime)
- **Toast**: "Переход на BYOK Starter выполнен. Ваш ключ настроен. Квота: 10,000 запросов/мес."

***

## СЦЕНАРИЙ 4: ПОЛЬЗОВАТЕЛЬ ДОБАВЛЯЕТ КЛЮЧ YANDEXGPT (BYOK)

**Контекст**: User Dashboard → Settings → API Keys → Add Your Key → Provider: YandexGPT
**UI компоненты**: Form, Input (API key), Input (Folder ID), Button (Validate \& Upgrade to BYOK), Alert, Toast, Help dialog

***

### E1: Invalid API Key (401)

**Триггер**: YandexGPT API возвращает 401 UNAUTHENTICATED

**Действия системы:**

1. Показать Alert (destructive) inline
2. Сохранить фокус на поле API Key
3. НЕ создавать subscription
4. Записать в audit log: `action: "byok_validation_failed", reason: "invalid_api_key", tenant_id: "..."`

**UI компоненты:**

```tsx
// Alert (destructive) inline
<Alert variant="destructive" className="mt-3">
  <XCircle className="h-4 w-4" />
  <AlertTitle>Ключ YandexGPT не прошёл проверку</AlertTitle>
  <AlertDescription>
    API ключ недействителен (ошибка 401). Переход на BYOK Starter невозможен.
    <div className="mt-2 text-sm">
      <strong>Что делать:</strong>
      <ol className="list-decimal ml-4 mt-1">
        <li>Проверьте формат ключа (должен начинаться с "AQVN...")</li>
        <li>Перевыпустите API ключ в <Link href="https://console.cloud.yandex.ru" className="underline">Yandex Cloud Console</Link></li>
        <li>Убедитесь, что ключ принадлежит сервисному аккаунту с ролью <code className="bg-muted px-1 py-0.5 rounded text-xs">ai.languageModels.user</code></li>
      </ol>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Ключ YandexGPT не прошёл проверку"
- **Описание**: "API ключ недействителен (ошибка 401). Переход на BYOK Starter невозможен."
- **Действие**: "Проверьте формат ключа. Перевыпустите API ключ в Yandex Cloud Console. Убедитесь, что ключ принадлежит сервисному аккаунту с ролью ai.languageModels.user."
- **Help link**: https://console.cloud.yandex.ru

***

### E2: N/A для YandexGPT

_(Scope mismatch не применим к YandexGPT)_

***

### E3: Permission Denied (403)

**Триггер**: YandexGPT API возвращает 403 PERMISSION_DENIED

**Действия системы:**

1. Показать Alert (warning) с пошаговой инструкцией
2. Highlight поле Folder ID (красная рамка)
3. НЕ создавать subscription
4. Записать в audit log: `action: "byok_validation_failed", reason: "permission_denied", folder_id: "..."`

**UI компоненты:**

```tsx
// Alert (warning) with detailed instructions
<Alert variant="warning" className="mt-3">
  <ShieldAlert className="h-4 w-4" />
  <AlertTitle>Нет доступа к YandexGPT API</AlertTitle>
  <AlertDescription>
    API ключ не имеет прав доступа к folder_id <code className="text-xs bg-muted px-1 py-0.5 rounded">{folderId}</code>.
    <div className="mt-3 text-sm space-y-2">
      <div className="font-medium">Как исправить:</div>
      <ol className="list-decimal ml-4 space-y-1">
        <li>Откройте <Link href="https://console.cloud.yandex.ru" className="underline">Yandex Cloud Console</Link></li>
        <li>Перейдите в раздел <strong>IAM и администрирование → Сервисные аккаунты</strong></li>
        <li>Выберите ваш сервисный аккаунт</li>
        <li>Нажмите <strong>Назначить роли</strong> → выберите <code className="bg-muted px-1 py-0.5 rounded text-xs">ai.languageModels.user</code></li>
        <li>Подождите 1-2 минуты (IAM синхронизация)</li>
        <li>Повторите попытку</li>
      </ol>
    </div>
    
    <div className="mt-3 flex gap-2">
      <Button 
        variant="outline" 
        size="sm" 
        onClick={() => window.open("https://yandex.cloud/ru/docs/iam/operations/sa/assign-role-for-sa")}
      >
        Инструкция с картинками
      </Button>
      <Button variant="default" size="sm" onClick={retry}>
        Повторить проверку
      </Button>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Нет доступа к YandexGPT API"
- **Описание**: "API ключ не имеет прав доступа к folder_id [ID]."
- **Действие**: "Пошаговая инструкция: 1) Откройте Yandex Cloud Console, 2) IAM → Сервисные аккаунты, 3) Назначьте роль ai.languageModels.user, 4) Подождите 1-2 минуты, 5) Повторите попытку."
- **Help link**: https://yandex.cloud/ru/docs/iam/operations/sa/assign-role-for-sa

***

### E4: Rate Limit Exceeded (429)

**Триггер**: YandexGPT API возвращает 429 RESOURCE_EXHAUSTED

**Действия системы:**

1. Показать Alert (warning) с countdown
2. Disable кнопку "Upgrade to BYOK" на 10 секунд
3. Автоматический retry через 10 секунд
4. Записать в audit log: `action: "byok_validation_failed", reason: "rate_limit_exceeded"`

**UI компоненты:**

```tsx
// Alert (warning) with countdown
<Alert variant="warning" className="mt-3">
  <Clock className="h-4 w-4" />
  <AlertTitle>Превышен лимит запросов YandexGPT API</AlertTitle>
  <AlertDescription>
    Вы отправили слишком много запросов за короткое время. YandexGPT ограничивает количество запросов в секунду.
    <div className="mt-2 flex items-center gap-2">
      <span className="text-sm">Повторная попытка через</span>
      <Badge variant="secondary" className="tabular-nums">{countdown} сек</Badge>
    </div>
    <Progress value={(10 - countdown) / 10 * 100} className="mt-2" />
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Превышен лимит запросов YandexGPT API"
- **Описание**: "Вы отправили слишком много запросов за короткое время. YandexGPT ограничивает количество запросов в секунду."
- **Действие**: "Повторная попытка через [countdown] секунд." (автоматически)

***

### E5: Network Timeout (504)

**Триггер**: httpx.TimeoutException (>10 секунд)

**Действия системы:**

1. Показать Alert (warning)
2. Предложить retry
3. НЕ создавать subscription
4. Записать в audit log: `action: "byok_validation_failed", reason: "network_timeout"`

**UI компоненты:**

```tsx
// Alert (warning)
<Alert variant="warning" className="mt-3">
  <Wifi className="h-4 w-4" />
  <AlertTitle>Не удалось проверить ключ</AlertTitle>
  <AlertDescription>
    Превышено время ожидания ответа от YandexGPT API (10 секунд). Возможны проблемы с интернет-соединением.
    <div className="mt-3 flex gap-2">
      <Button variant="default" size="sm" onClick={retry}>
        Повторить попытку
      </Button>
      <Button variant="outline" size="sm" onClick={cancel}>
        Отменить
      </Button>
    </div>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Не удалось проверить ключ"
- **Описание**: "Превышено время ожидания ответа от YandexGPT API (10 секунд). Возможны проблемы с интернет-соединением."
- **Действие**: "Повторить попытку или отменить."

***

### E6: Provider Server Error (500)

**Триггер**: YandexGPT API возвращает 500 INTERNAL

**Действия системы:**

1. Показать Alert (destructive)
2. НЕ создавать subscription
3. Записать в audit log + error log
4. Показать Request ID (из google.rpc.RequestInfo)

**UI компоненты:**

```tsx
// Alert (destructive)
<Alert variant="destructive" className="mt-3">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Ошибка сервиса YandexGPT</AlertTitle>
  <AlertDescription>
    YandexGPT API временно недоступен (ошибка 500). Переход на BYOK Starter отложен до восстановления сервиса.
    <div className="mt-2 text-xs text-muted-foreground font-mono">
      Request ID: {requestId}
    </div>
    <div className="mt-2 text-sm">
      Ваша подписка Managed Starter остаётся активной. Попробуйте повторить миграцию позже.
    </div>
    <Button variant="outline" size="sm" className="mt-3" onClick={close}>
      Понятно
    </Button>
  </AlertDescription>
</Alert>
```

**Текст сообщения:**

- **Заголовок**: "Ошибка сервиса YandexGPT"
- **Описание**: "YandexGPT API временно недоступен (ошибка 500). Переход на BYOK Starter отложен до восстановления сервиса."
- **Действие**: "Ваша подписка Managed Starter остаётся активной. Попробуйте повторить миграцию позже."
- **Request ID**: из response (google.rpc.RequestInfo)

***

### S1: Success (200) → Upgrade Confirmation

**Триггер**: YandexGPT API возвращает 200 OK

**Действия системы:**

1. Показать Alert (success)
2. Показать Confirmation Dialog с деталями миграции
3. Записать в audit log: `action: "byok_validation_success", provider: "yandexgpt", folder_id: "..."`

**UI компоненты:**

```tsx
// Step 1: Alert (success) after validation
<Alert variant="success" className="mt-3">
  <CheckCircle className="h-4 w-4" />
  <AlertTitle>Ключ YandexGPT действителен</AlertTitle>
  <AlertDescription>
    API ключ имеет доступ к folder_id <code className="text-xs bg-green-100 px-1 py-0.5 rounded">{folderId}</code>. 
    Ключ готов к использованию.
    <div className="mt-2 text-sm text-muted-foreground">
      Квота BYOK Starter: 10,000 запросов в месяц (в 10 раз больше текущей).
    </div>
  </AlertDescription>
</Alert>

// Step 2: Confirmation Dialog (same structure as GigaChat)
<Dialog open={showConfirmation}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Подтвердите переход на BYOK Starter</DialogTitle>
      <DialogDescription>
        Ваша подписка будет обновлена. Данные о миграции:
      </DialogDescription>
    </DialogHeader>
    
    <div className="space-y-4 py-4">
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="text-muted-foreground">Текущий тариф:</div>
        <div className="font-medium">Managed Starter (1,990 ₽/мес)</div>
        
        <div className="text-muted-foreground">Новый тариф:</div>
        <div className="font-medium">BYOK Starter (2,990 ₽/мес)</div>
        
        <div className="text-muted-foreground">Разница:</div>
        <div className="font-medium text-orange-600">+1,000 ₽/мес</div>
        
        <div className="text-muted-foreground">Квота:</div>
        <div className="font-medium">10,000 запросов/мес (×10)</div>
        
        <div className="text-muted-foreground">Provider:</div>
        <div className="font-medium">YandexGPT</div>
        
        <div className="text-muted-foreground">Folder ID:</div>
        <div className="font-mono text-xs bg-muted px-2 py-1 rounded">{folderId}</div>
        
        <div className="text-muted-foreground">Downtime:</div>
        <div className="font-medium">~5 секунд (перезапуск бота)</div>
      </div>
      
      <Separator />
      
      <Alert variant="info">
        <Info className="h-4 w-4" />
        <AlertDescription className="text-sm">
          Следующий платёж будет списан по новому тарифу через {daysUntilBilling} дней 
          (<strong>{nextBillingDate}</strong>). Ваш ключ будет зашифрован и сохранён.
        </AlertDescription>
      </Alert>
    </div>
    
    <DialogFooter>
      <Button variant="outline" onClick={cancel}>
        Отменить
      </Button>
      <Button variant="default" onClick={confirmUpgrade} loading={isUpgrading}>
        {isUpgrading ? "Обновление..." : "Подтвердить и перейти на BYOK"}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>

// Step 3: Toast (after successful migration)
toast({
  title: "Переход на BYOK Starter выполнен",
  description: "Ваш ключ YandexGPT настроен. Квота: 10,000 запросов/мес. Следующий платёж: 2,990 ₽ через 28 дней.",
  variant: "default",
  duration: 7000,
});
```

**Текст сообщения:**

- **Alert Title**: "Ключ YandexGPT действителен"
- **Alert Description**: "API ключ имеет доступ к folder_id [ID]. Ключ готов к использованию. Квота BYOK Starter: 10,000 запросов в месяц (в 10 раз больше текущей)."
- **Dialog Title**: "Подтвердите переход на BYOK Starter"
- **Dialog Description**: Таблица с деталями миграции (тариф, цена, квота, provider, folder_id, downtime)
- **Toast**: "Переход на BYOK Starter выполнен. Ваш ключ YandexGPT настроен. Квота: 10,000 запросов/мес."

***

## СВОДНАЯ ТАБЛИЦА: МАТРИЦА СООБЩЕНИЙ

| Сценарий | Ошибка | Заголовок | Действие | Состояние |
| :-- | :-- | :-- | :-- | :-- |
| **Админ + GigaChat** | E1 (401) | "Ключ GigaChat недействителен" | Перевыпустите в Studio | Модальное окно открыто |
|  | E2 (400) | "Ключ не соответствует версии API" | Использовать тип GIGACHAT_API_B2B (auto-fix) | Модальное окно открыто |
|  | E4 (429) | "Превышен лимит запросов" | Повторная попытка через 30 сек (auto-retry) | Кнопка disabled |
|  | E5 (504) | "Не удалось связаться с GigaChat API" | Повторить попытку или отменить | Модальное окно открыто |
|  | E6 (500) | "Внутренняя ошибка GigaChat API" | Повторить позже | Модальное окно открыто |
|  | S1 (200) | "Ключ GigaChat действителен" | Scope auto-filled → Add Key | Enable кнопка Add |
| **Админ + YandexGPT** | E1 (401) | "Ключ YandexGPT недействителен" | Перевыпустите в Yandex Cloud Console | Модальное окно открыто |
|  | E3 (403) | "Нет доступа к YandexGPT API" | Назначьте роль ai.languageModels.user | Highlight Folder ID |
|  | E4 (429) | "Превышен лимит запросов" | Повторная попытка через 10 сек (auto-retry) | Кнопка disabled |
|  | E5 (504) | "Не удалось связаться с YandexGPT API" | Повторить попытку или отменить | Модальное окно открыто |
|  | E6 (500) | "Внутренняя ошибка YandexGPT API" | Повторить позже (+ Request ID) | Модальное окно открыто |
|  | S1 (200) | "Ключ YandexGPT действителен" | Folder ID verified → Add Key | Enable кнопка Add |
| **User + GigaChat** | E1 (401) | "Ключ GigaChat не прошёл проверку" | Убедитесь, что ключ скопирован полностью | Форма активна |
|  | E2 (400) | "Тип ключа определён автоматически" | Продолжить с GIGACHAT_API_B2B (auto) | Форма активна |
|  | E4 (429) | "Превышен лимит запросов GigaChat API" | Повторная попытка через 30 сек (auto-retry) | Кнопка disabled |
|  | E5 (504) | "Не удалось проверить ключ" | Повторить попытку или отменить | Форма активна |
|  | E6 (500) | "Ошибка сервиса GigaChat" | Managed остаётся активной, попробуйте позже | Форма активна |
|  | S1 (200) | "Ключ GigaChat действителен" | Показать Confirmation Dialog → Upgrade | Confirmation dialog |
| **User + YandexGPT** | E1 (401) | "Ключ YandexGPT не прошёл проверку" | Проверьте формат ключа (AQVN...) | Форма активна |
|  | E3 (403) | "Нет доступа к YandexGPT API" | Пошаговая инструкция (6 steps) | Highlight Folder ID |
|  | E4 (429) | "Превышен лимит запросов YandexGPT API" | Повторная попытка через 10 сек (auto-retry) | Кнопка disabled |
|  | E5 (504) | "Не удалось проверить ключ" | Повторить попытку или отменить | Форма активна |
|  | E6 (500) | "Ошибка сервиса YandexGPT" | Managed остаётся активной, попробуйте позже | Форма активна |
|  | S1 (200) | "Ключ YandexGPT действителен" | Показать Confirmation Dialog → Upgrade | Confirmation dialog |


***

## КЛЮЧЕВЫЕ ПРИНЦИПЫ (semantic_core_ru_v1.1.md)

### Tone of Voice

- ✅ **Формальный**, но не бюрократичный
- ✅ **Data-driven** — точные метрики (30 сек, 10,000 запросов)
- ✅ **Action-oriented** — всегда указываем, что делать дальше
- ✅ **Спокойный** — без паники, без восклицательных знаков в ошибках
- ✅ **Прозрачность** — объясняем, почему произошла ошибка


### Структура сообщений

1. **Заголовок** (8-10 слов) — что случилось
2. **Описание** (1-2 предложения) — почему/детали
3. **Действие** (numbered list или кнопка) — что делать дальше
4. **Help link** (опционально) — ссылка на docs

### UI компоненты

- Alert (destructive/warning/info/success)
- Toast (для quick feedback)
- Dialog (для confirmation)
- Progress bar (для countdown)
- Badge (для таймеров)

***

**Версия матрицы**: 1.0.0
**Готово к реализации**: Week 20-21
<span style="display:none">[^1][^10][^2][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: semantic_core_ru_v1.1.md

[^2]: strategy_hybrid_model.md

[^3]: UI_SCREENS_STRATEGIC_MAP_v1.0.0.md

[^4]: DOCUMENTATION_INDEX.md

[^5]: AUTH_ARCHITECTURE_TOKENS.md

[^6]: AUTH_HYBRID_MODEL.md

[^7]: WEEK9_COMPLETE_UI_DESIGN_SYSTEM.md

[^8]: prompt3.md

[^9]: prompt2.md

[^10]: prompt1.md

