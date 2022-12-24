import aiohttp
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import config

HEADERS = {
    'content-type': 'application/json',
    'authorization': config.API_TOKEN
}


# Вспомогательные функции для получения данных которые используются только в этом модуле
# *******************************************************************************************


# базовая проверка перед оплатой Заказа
def check_before_payment(order_info: dict) -> str:
    result = ''

    if 'error' in order_info:
        result = 'На сервере произошел сбой. Мы работаем над исправлением.'
        return result

    if order_info.get('amount', 0) < 1:
        result = 'Заказ с нулевой суммой. Добавьте другой товар.'
        return result

    return result


async def get_order(session: aiohttp.ClientSession,  order_pk: int, paid: int) -> dict:
    order_info = {}
    params_get = {'pk': order_pk, 'paid': paid}

    async with session.get(f'{config.ADDR_SERV}/api/v1/orders', params=params_get) as resp:
        if resp.ok:
            orders = await resp.json()

            if orders:
                order_info = orders[0]

    return order_info


async def get_category_by_pk(session: aiohttp.ClientSession, category_pk: str) -> dict:
    category_info = {}

    async with session.get(f'{config.ADDR_SERV}/api/v1/products/categories/{category_pk}') as resp:
        if resp.ok:
            category_info = await resp.json()

    return category_info


# получим комплексную инфу о товаре (остатки и цены) и добавим последнюю цену на него
async def get_product_by_pk(session: aiohttp.ClientSession, product_pk: str) -> dict:
    product_info = {}

    async with session.get(f'{config.ADDR_SERV}/api/v1/products/{product_pk}') as resp:
        if resp.ok:
            product_info = await resp.json()
            all_prices = product_info.get('get_prices', [])
            product_info['price'] = 0.0
            product_info['discount_percentage'] = 0

            if all_prices:
                product_info['price'] = all_prices[-1].get('price', 0.0)
                product_info['discount_percentage'] = all_prices[-1].get(
                    'discount_percentage', 0)

    return product_info


# получим одну строку товара из Корзины или Заказа из API списка(Retrieve не реализовал на Django, не нужен)
async def get_cart_product(session: aiohttp.ClientSession, cart_order_pk: int, product_pk: int, id_messenger: int, for_order=False) -> dict:
    product_cart_info = {}
    params_get = {'product': product_pk, 'id_messenger': id_messenger}

    if for_order:
        params_get['order'] = cart_order_pk
    else:
        params_get['cart'] = cart_order_pk

    async with session.get(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart', params=params_get) as resp:
        if resp.ok:
            product_carts = await resp.json()

            if product_carts:
                product_cart_info = product_carts[0]
                product_cart_info['pk'] = product_cart_info.get('id', 0)

    return product_cart_info


# получим все строки товаров из Корзины
async def get_cart_products(session: aiohttp.ClientSession, cart_pk: int, id_messenger: int) -> list[dict]:
    product_carts = []
    params_get = {'cart': cart_pk, 'id_messenger': id_messenger}

    async with session.get(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart', params=params_get) as resp:
        if resp.ok:
            product_carts = await resp.json()

    return product_carts


# получает товары в Заказе (product_to_cart - общая таблица как для строк корзины так и для строк заказов)
async def get_order_products(session: aiohttp.ClientSession, order_pk: str) -> list[dict]:
    product_order = []
    params_get = {'order': order_pk}

    async with session.get(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart', params=params_get) as resp:
        if resp.ok:
            product_order = await resp.json()

    return product_order


#  получает pk статуса по представлению
async def get_status(session: aiohttp.ClientSession, name: str = '', for_bot: int = 1) -> int:
    status_pk = 0
    params_get = {'name': name, 'for_bot': for_bot}

    async with session.get(f'{config.ADDR_SERV}/api/v1/statuses', params=params_get) as resp:
        if resp.ok:
            statuses = await resp.json()
            status_pk = statuses[0]['id']

    return status_pk


async def get_payment_type(session: aiohttp.ClientSession) -> int:
    payment_type_pk = 0
    params_get = {'for_bot': 1}

    async with session.get(f'{config.ADDR_SERV}/api/v1/payment_types', params=params_get) as resp:
        if resp.ok:
            payment_types = await resp.json()
            payment_type_pk = payment_types[0]['id']

    return payment_type_pk


async def get_delivery_type(session: aiohttp.ClientSession) -> int:
    delivery_type_pk = 0
    params_get = {'for_bot': 1}

    async with session.get(f'{config.ADDR_SERV}/api/v1/delivery_types', params=params_get) as resp:
        if resp.ok:
            delivery_types = await resp.json()
            delivery_type_pk = delivery_types[0]['id']

    return delivery_type_pk


# проверка есть ли в корзине пользователя товары
async def check_cart(id_messenger: int) -> bool:
    product_carts = None

    cart_info = await get_cart_info(id_messenger)
    product_carts = cart_info['products']

    return True if not product_carts else False


# Конец блока вспомогательных функций
# *******************************************************************************************


async def get_start_menu(id_messenger: int = 0) -> ReplyKeyboardMarkup:
    cart_quantity = ''

    if id_messenger:
        cart_info = await get_cart_info(id_messenger)
        count_products = len(cart_info.get('products', []))

        if count_products:
            cart_quantity = f"({count_products})"

    kb_start = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb_menu_btn_select = KeyboardButton(text='📦Товары')
    kb_menu_btn_cart = KeyboardButton(text=f'🛒Корзина{cart_quantity}')
    kb_menu_btn_start = KeyboardButton(text='/start')
    kb_menu_btn_order = KeyboardButton(text='🧾Оформить заказ')
    kb_menu_btn_order_list_unpaid = KeyboardButton(text='💼Неоплаченные заказы')
    kb_menu_btn_order_list_paid = KeyboardButton(text='💼💰Оплаченные заказы')
    kb_start.add(kb_menu_btn_select)
    kb_start.insert(kb_menu_btn_cart)
    kb_start.add(kb_menu_btn_start)
    kb_start.insert(kb_menu_btn_order)
    kb_start.add(kb_menu_btn_order_list_unpaid)
    kb_start.insert(kb_menu_btn_order_list_paid)

    return kb_start


# Формирует кнопку отправки контакта
async def get_contact_kb() -> ReplyKeyboardMarkup:
    kb_contact = ReplyKeyboardMarkup(resize_keyboard=False)
    new_button = KeyboardButton(text='📱 Отправить номер телефона',
                                request_contact=True)
    kb_contact.add(new_button)

    return kb_contact


# общий диалог Да-Нет для многих функций
async def get_answer_yes_no_kb() -> InlineKeyboardMarkup:
    kb_yes_no = InlineKeyboardMarkup(row_width=2)

    button_yes = InlineKeyboardButton(
        text='Да',
        callback_data='answer_yes_no1'
    )

    kb_yes_no.add(button_yes)

    button_no = InlineKeyboardButton(
        text='Нет',
        callback_data='answer_yes_no0'
    )

    kb_yes_no.insert(button_no)

    return kb_yes_no


# Получим список категорий товаров
# если category_pk = 0, тогда получим только корневые группы товаров, иначе получим товары в подгруппе,
# при этом проверим nested_category, если список пуст, тогда в группе нет подгрупп, есть только товары или она пустая
async def get_categories(category_pk: int = 0) -> InlineKeyboardMarkup:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        params_get = {'category_pk': category_pk} if category_pk else {
            'top_level_only': 1}

        async with session.get(f'{config.ADDR_SERV}/api/v1/products/categories', params=params_get) as resp:
            categories = await resp.json()
            kb_categories = InlineKeyboardMarkup(row_width=1)

            if 'detail' in categories:
                new_button = InlineKeyboardButton(
                    text=categories['detail'],
                    callback_data=f'category_nested_pk'
                )
                kb_categories.add(new_button)
                return kb_categories

            for category in categories:
                subcategories = category.get('nested_category', [])
                category_pk = category.get('pk', ' ')

                if subcategories:
                    new_button = InlineKeyboardButton(
                        text=category.get('name', ' '),
                        callback_data=f'category_nested_pk{category_pk}'
                    )
                else:
                    new_button = InlineKeyboardButton(
                        text=category.get('name', ' '),
                        callback_data=f'category_pk{category_pk}'
                    )

                kb_categories.add(new_button)

            button_cancel = InlineKeyboardButton(
                text='Отмена', callback_data='cancel'
            )
            kb_categories.add(button_cancel)

    return kb_categories


async def get_product_list(category_pk: str) -> InlineKeyboardMarkup:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        params_get = {'category_pk': category_pk}

        async with session.get(f'{config.ADDR_SERV}/api/v1/products', params=params_get) as resp:
            products = await resp.json()
            kb_products = InlineKeyboardMarkup(row_width=1)

            for product in products:
                name = product.get('name', ' ')
                product_pk = product.get('pk', ' ')

                new_button = InlineKeyboardButton(
                    text=name,
                    callback_data=f'show_product{product_pk}'
                )
                kb_products.add(new_button)

            button_back = InlineKeyboardButton(
                text='Отмена', callback_data='cancel'
            )
            kb_products.add(button_back)

    return kb_products


# выводит карточку товара и предложение добавить в корзину
async def get_product_info(product_pk: str) -> tuple[InlineKeyboardMarkup, str, str]:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        kb_product = InlineKeyboardMarkup(row_width=1)
        product_info = await get_product_by_pk(session, product_pk)
        url_photo = product_info.get('photo', '')
        price = product_info.get('price', 0.00)
        currency_sign = ''

        if product_info['get_prices']:
            price_info = product_info['get_prices'][0]
            currency_sign = price_info['currency']['sign']

        stock_products = product_info.get('get_stock_product', [])
        info = f"{product_info.get('name', '')}\n----------\nналичие:\n"

        if stock_products:
            for stock in stock_products:
                info += f"{stock['warehouse']['city']} - {stock['stock'].split('.')[0]} шт.\n"

            info += f'Цена: {price}{currency_sign}'

            new_button = InlineKeyboardButton(
                text='🛒 Добавить в корзину',
                callback_data=f'add_product_to_cart{product_pk}'
            )
            kb_product.add(new_button)
        else:
            info += 'нет в наличии'

    return kb_product, info, url_photo


# выводим кнопку с подтверждением добавления товара в корзину и заодно пробрасываем его pk далее по машинным состояниям
async def get_confirm_add_product_to_cart(product_pk: str) -> InlineKeyboardMarkup:

    kb_confirm = InlineKeyboardMarkup(row_width=2)
    confirm_button = InlineKeyboardButton(
        text='Да',
        callback_data=f'confirm_add_product_to_cart{product_pk}'
    )
    not_confirm_button = InlineKeyboardButton(
        text='Нет',
        callback_data=f'not_confirm_add_product_to_cart{product_pk}'
    )
    kb_confirm.add(confirm_button).insert(not_confirm_button)

    return kb_confirm


# получим кнопки складов, но только тех, где есть товар в нужном количестве
async def get_warehouses_kb(product_pk: str, quantity_msg: str) -> InlineKeyboardMarkup:
    quantity = float(quantity_msg)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        kb_warehouses = InlineKeyboardMarkup(row_width=1)
        product = await get_product_by_pk(session, product_pk)
        stock_products = product.get('get_stock_product', [])

        for stock in stock_products:
            if quantity > float(stock['stock']):
                continue

            new_button = InlineKeyboardButton(
                text=stock['warehouse']['name'],
                callback_data=f"warehouse_pk{stock['warehouse']['pk']}"
            )
            kb_warehouses.add(new_button)

    return kb_warehouses


async def get_cart_info(id_messenger: int) -> dict:
    cart_info = {}
    params_get = {'id_messenger': id_messenger}

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(f'{config.ADDR_SERV}/api/v1/get_cart_info', params=params_get) as resp:
            if resp.ok:
                cart_info = await resp.json()

    return cart_info


# возвращает данные о товарах в корзине в виде словаря, где ключем является строка с данными о товаре,
# а значением кнопка действия с этим товаром(например "Удалить")
async def get_cart(id_messenger: int) -> dict:
    cart_products = {'amount_cart': 0.0}

    cart_info = await get_cart_info(id_messenger)
    currency_sign = cart_info['currency']['sign']
    cart_products['current_sign'] = currency_sign

    products_in_cart = cart_info.get('products', [])

    for product_row in products_in_cart:
        cart_products['amount_cart'] += float(product_row['amount'])
        product_info = f"<strong>{product_row['product']['name']}</strong>\nКоличество: {product_row['quantity'].split('.')[0]}\nСумма: {product_row['amount']}{currency_sign}"

        kb_cart = InlineKeyboardMarkup(row_width=2)

        info_button = InlineKeyboardButton(
            text='📦 О товаре',
            callback_data=f"show_product{product_row['product']['pk']}"
        )
        delete_button = InlineKeyboardButton(
            text='🗑️ Удалить',
            callback_data=f"delete_product_from_cart{product_row['product']['pk']}"
        )

        kb_cart.add(info_button).insert(delete_button)

        cart_products[product_info] = kb_cart

    return cart_products


# Добавляет товар в корзину
# product_cart_new - словарь с данными которые ввел пользователь в машинном состоянии
async def add_product_to_cart(product_cart_new: dict) -> None:
    product_cart_new['product_pk'] = int(product_cart_new.get('product_pk', 0))
    product_cart_new['quantity'] = float(product_cart_new.get('quantity', 0.0))
    product_cart_new['warehouse_pk'] = int(product_cart_new.get('warehouse_pk', 0))
    product_cart_new['for_anonymous_user'] = 1

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.post(f'{config.ADDR_SERV}/api/v1/update_product_to_cart', json=product_cart_new):
            pass


# удаляет товар из корзины или заказа, так как строки принадлежат и корзинам и заказам
async def delete_product_from_cart(product_cart_info: dict) -> None:
    product_cart_info['product_pk'] = int(
        product_cart_info.get('product_pk', 0))
    product_cart_info['for_anonymous_user'] = 1

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.post(f'{config.ADDR_SERV}/api/v1/delete_product_from_cart', json=product_cart_info):
            pass


# Создает Заказ в БД сайта или добавляет товары из корзины к существующему Заказу
# и возвращает обновленную инфу о заказе
# пример order_info : {'first_name': 'Иван', 'last_name': 'Иванов', 'phone': '79277777777', 'id_messenger': 827503364}
async def create_or_update_order(order_info: dict) -> dict:
    order_info['id'] = 0

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.post(f'{config.ADDR_SERV}/api/v1/create_update_order', json=order_info) as resp:
            if resp.ok:
                order_info = await resp.json()

    return order_info


# Получу заказы привязанные к id_messenger функция имеет смысл только для ТелеграмМагазина
async def get_orders_for_messenger(id_messenger: int, paid: int) -> list[dict]:
    orders = []

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        params_get = {'id_messenger': id_messenger, 'paid': paid}

        async with session.get(f'{config.ADDR_SERV}/api/v1/orders', params=params_get) as resp:
            if resp.ok:
                orders = await resp.json()

    return orders


# получим список заказов покупателя в виде кнопок InlineKeyboardMarkup
async def get_kb_order_list(id_messenger: int, paid: int) -> InlineKeyboardMarkup:
    kb_orders = InlineKeyboardMarkup(row_width=1)

    orders = await get_orders_for_messenger(id_messenger, paid)

    for order in orders:
        paid_text = 'оплачен' if paid else 'неоплачен'
        date_order = datetime.strptime(
            order['time_update'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d.%m.%Y')
        text_order = f"Заказ №{order['id']} от {date_order} статус: {paid_text}"
        order_pk = order.get('id', 0)

        order_button = InlineKeyboardButton(
            text=text_order,
            callback_data=f'show_order_pk{order_pk}:{paid}'
        )
        kb_orders.add(order_button)

        if not paid:
            amount = order.get('amount', 0)
            payment_button = InlineKeyboardButton(
                text=f"💳Оплатить {amount}{order['currency']['sign']}",
                callback_data=f"payment_for_order{order_pk}:{amount}"
            )
            kb_orders.add(payment_button)

    button_cancel = InlineKeyboardButton(
        text='Отмена', callback_data='cancel'
    )
    kb_orders.add(button_cancel)

    return kb_orders


async def get_order_info(order_pk: str, paid: int) -> dict:
    order_info = {}
    params_get = {'order_pk': order_pk, 'paid': paid}

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(f'{config.ADDR_SERV}/api/v1/get_order_info', params=params_get) as resp:
            if resp.ok:
                order_info = await resp.json()

                if order_info:
                    date_order = datetime.strptime(
                        order_info['time_update'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d.%m.%Y')
                    order_info['order_repr'] = f"<strong>Заказ №{order_info['id']} от {date_order}\n</strong>"

    return order_info


# возвращает данные о товарах в заказе в виде словаря, где ключом является строка с данными о товаре,
# а значением кнопка действия с этим товаром(например "Удалить") и данные о самом заказе в виде словаря
async def get_kb_order_info(order_pk: str, paid: int) -> tuple[dict, dict]:
    order_products_kb = {}
    order_info = await get_order_info(order_pk, paid)
    currency_sign = order_info['currency']['sign']
    products_in_order = order_info.get('products', [])

    for product_row in products_in_order:
        product_info = f"<strong>{product_row['product']['name']}</strong>\nКоличество: {product_row['quantity'].split('.')[0]} на сумму: {product_row['amount']}{currency_sign}"

        kb_cart = InlineKeyboardMarkup(row_width=2)

        info_button = InlineKeyboardButton(
            text='📦 О товаре',
            callback_data=f"show_product{product_row['product']['pk']}"
        )
        kb_cart.add(info_button)

        if not order_info['paid']:
            delete_button = InlineKeyboardButton(
                text='🗑️ Удалить',
                callback_data=f"delete_product_from_order{product_row['product']['pk']}:{order_pk}"
            )
            kb_cart.insert(delete_button)

        order_products_kb[product_info] = kb_cart

    # если товары есть и он не оплачен, то к последнему товару добавим кнопку оплаты всего заказа
    if order_products_kb and not paid:
        amount = order_info.get('amount', 0)
        payment_button = InlineKeyboardButton(
            text=f"💳Оплатить {amount}{currency_sign}",
            callback_data=f"payment_for_order{order_pk}:{amount}"
        )
        order_products_kb[product_info].add(payment_button)

    return order_products_kb, order_info


# Проверяет достаточно ли товара для отгрузки
# difference_info - словарь Наименование товара:Разница остатков, если пустой, то всего хватает
async def check_stock_in_order(order_pk: str) -> dict:
    difference_info = {}

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        params_get = {'order_pk': order_pk}

        async with session.get(f'{config.ADDR_SERV}/api/v1/check_stock_for_order', params=params_get) as resp:
            if resp.ok:
                difference_info = await resp.json()

    return difference_info


# после оплаты установим признак Оплачен в БД
async def set_order_payment(order_pk: str) -> None:
    order_info = {'paid': 1}

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.patch(f'{config.ADDR_SERV}/api/v1/orders_update/{order_pk}', json=order_info):
            pass
