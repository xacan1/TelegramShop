import aiohttp
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
# from aiogram.utils.callback_data import CallbackData
import config

HEADERS = {
    'content-type': 'application/json',
    'authorization': config.API_TOKEN
}


# Вспомогательные функции для получения данных
# *******************************************************************************************


# получаем id текущего пользовтеля по его токену передаваемому всегда в заголовке запроса
async def getUserByToken(session: aiohttp.ClientSession) -> int:
    user_pk = 0

    async with session.get(f'{config.ADDR_SERV}/api/v1/tokens') as resp:
        if resp.ok:
            tokens = await resp.json()
            user_pk = tokens[0].get('user', 0) if tokens else 0

    return user_pk


async def getCartForUser(session: aiohttp.ClientSession, user_pk: int) -> dict:
    cart_info = {}

    async with session.get(f'{config.ADDR_SERV}/api/v1/carts/{user_pk}') as resp:
        if resp.ok:
            cart_info = await resp.json()
        else:
            # если нет корзины, то создадим ее
            body_request = {'user': user_pk, 'quantity': 0.0, 'amount': 0.0,
                            'discount': 0.0, 'in_order': False, 'for_anonymous_user': True}

            async with session.post(f'{config.ADDR_SERV}/api/v1/carts_create', json=body_request) as resp:
                cart_info = await resp.json()

    return cart_info


async def getCategoryByPK(session: aiohttp.ClientSession, category_pk: str) -> dict:
    category_info = {}

    async with session.get(f'{config.ADDR_SERV}/api/v1/products/categories/{category_pk}') as resp:
        if resp.ok:
            category_info = await resp.json()

    return category_info


# получим инфу о товаре и добавим последнюю цену на него
async def getProductByPK(session: aiohttp.ClientSession, product_pk: str) -> dict:
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
async def getCartProduct(session: aiohttp.ClientSession, cart_order_pk: int, product_pk: int, id_messenger: int, for_order=False) -> dict:
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
async def getCartProducts(session: aiohttp.ClientSession, cart_pk: int, id_messenger: int) -> list:
    product_carts = []
    params_get = {'cart': cart_pk, 'id_messenger': id_messenger}

    async with session.get(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart', params=params_get) as resp:
        if resp.ok:
            product_carts = await resp.json()

    return product_carts


# получает товары в Заказе (product_to_cart - общая таблица как для строк корзины так и для строк заказов)
async def getOrderProducts(session: aiohttp.ClientSession, order_pk: str) -> list:
    product_order = []
    params_get = {'order': order_pk}

    async with session.get(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart', params=params_get) as resp:
        if resp.ok:
            product_order = await resp.json()

    return product_order


async def getStatus(session: aiohttp.ClientSession) -> int:
    status_pk = 0
    params_get = {'for_bot': 1}

    async with session.get(f'{config.ADDR_SERV}/api/v1/statuses', params=params_get) as resp:
        if resp.ok:
            statuses = await resp.json()
            status_pk = statuses[0]['id']

    return status_pk


async def getPaymentType(session: aiohttp.ClientSession) -> int:
    payment_type_pk = 0
    params_get = {'for_bot': 1}

    async with session.get(f'{config.ADDR_SERV}/api/v1/payment_types', params=params_get) as resp:
        if resp.ok:
            payment_types = await resp.json()
            payment_type_pk = payment_types[0]['id']

    return payment_type_pk


async def getDeliveryType(session: aiohttp.ClientSession) -> int:
    delivery_type_pk = 0
    params_get = {'for_bot': 1}

    async with session.get(f'{config.ADDR_SERV}/api/v1/delivery_types', params=params_get) as resp:
        if resp.ok:
            delivery_types = await resp.json()
            delivery_type_pk = delivery_types[0]['id']

    return delivery_type_pk


async def checkCart(id_messenger: int) -> bool:
    product_carts = []

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        user_pk = await getUserByToken(session)
        cart_info = await getCartForUser(session, user_pk)
        cart_pk = cart_info.get('pk', 0)
        product_carts = await getCartProducts(session, cart_pk, id_messenger)

    return True if not product_carts else False


# Конец блока вспомогательных функций
# *******************************************************************************************


async def get_start_menu() -> ReplyKeyboardMarkup:
    kb_start = ReplyKeyboardMarkup(resize_keyboard=True)
    kb_menu_btn_select = KeyboardButton(text='/📦Товары')
    kb_menu_btn_cart = KeyboardButton(text='/🛒Корзина')
    kb_menu_btn_order = KeyboardButton(text='/🧾Заказ')
    kb_menu_btn_order_list = KeyboardButton(text='/💼Ваши_заказы')
    kb_start.add(kb_menu_btn_select)
    kb_start.insert(kb_menu_btn_cart)
    kb_start.insert(kb_menu_btn_order)
    kb_start.insert(kb_menu_btn_order_list)

    return kb_start


# Формирует кнопку отправки контакта
async def get_contact_kb() -> ReplyKeyboardMarkup:
    kb_contact = ReplyKeyboardMarkup(resize_keyboard=True)
    new_button = KeyboardButton(text='📱 Отправить номер телефона',
                                request_contact=True)
    kb_contact.add(new_button)

    return kb_contact


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


# Выведем кнопку оплаты заказа
async def get_payments_kb() -> InlineKeyboardMarkup:
    kb_payment = InlineKeyboardMarkup(row_width=1)
    button = InlineKeyboardButton(
        text='Оплатить через ЮKassa',
        callback_data='payment_yookassa'
    )
    kb_payment.add(button)


# Получим список категорий товаров
# если category_pk = 0, тогда получим только корневые группы товаров, иначе получим товары в подгруппе,
# при этом проверим nested_category, если список пуст, тогда в группе нет подгрупп, есть только товары или она пустая
async def get_categories(category_pk=0) -> InlineKeyboardMarkup:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        params_get = {'category_pk': category_pk} if category_pk else {
            'top_level_only': 1}

        async with session.get(f'{config.ADDR_SERV}/api/v1/products/categories', params=params_get) as resp:
            categories = await resp.json()
            kb_categories = InlineKeyboardMarkup(row_width=1)

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
async def get_product_info(product_pk: str) -> tuple:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        product_info = await getProductByPK(session, product_pk)
        url_photo = product_info.get('photo', '')
        price = product_info.get('price', 0.00)
        stock_products = product_info.get('get_stock_product', [])
        info_str = f"{product_info.get('name', '')}\n----------\nналичие:\n"

        for stock in stock_products:
            info_str += f"{stock['warehouse']['city']} - {stock['stock'].split('.')[0]} шт.\n"

        info_str += f'Цена: {price}₽'

        kb_product = InlineKeyboardMarkup(row_width=1)
        new_button = InlineKeyboardButton(
            text='🛒 Добавить в корзину',
            callback_data=f'add_product_to_cart{product_pk}'
        )
        kb_product.add(new_button)

    return kb_product, info_str, url_photo


# выводим кнопку с подтверждением добавления товара в корзину и заодно пробрасываем его pk
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
        product = await getProductByPK(session, product_pk)
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


# возвращает данные о товарах в корзине в виде словаря, где ключем является строка с данными о товаре,
# а значением кнопка действия с этим товаром(например "Удалить")
async def get_cart(id_messenger: int) -> dict:
    cart_products = {'amount_cart': 0.0}

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        user_pk = await getUserByToken(session)
        cart_info = await getCartForUser(session, user_pk)
        cart_pk = cart_info.get('pk', 0)
        products_in_cart = await getCartProducts(session, cart_pk, id_messenger)

        for product in products_in_cart:
            cart_products['amount_cart'] += float(product['amount'])
            product_info = f"<strong>{product['product']['name']}</strong>\nКоличество: {product['quantity'].split('.')[0]}\nСумма: {product['amount']}₽"

            kb_cart = InlineKeyboardMarkup(row_width=2)

            info_button = InlineKeyboardButton(
                text='📦 О товаре',
                callback_data=f"show_product{product['product']['pk']}"
            )
            delete_button = InlineKeyboardButton(
                text='🚽 Удалить',
                callback_data=f"delete_product_from_cart{product['product']['pk']}"
            )

            kb_cart.add(info_button).insert(delete_button)

            cart_products[product_info] = kb_cart

    return cart_products


# Добавляет товар в корзину
# product_cart_new - словарь с данными которые ввел пользователь
# скидку считаем не на штуку а на всё количество товара
async def add_product_to_cart(product_cart_new: dict) -> None:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # сначала нужно найти строку корзины с этим же товаром, вдруг мы добавляем тот же товар еще раз, значит нужно будет суммировать количество в корзине
        user_pk = await getUserByToken(session)
        cart_info = await getCartForUser(session, user_pk)
        cart_pk = cart_info.get('pk', 0)
        # Теперь заполним данные о строке товара в корзине
        body_request = {}
        # body_request = {'id_messenger': '', 'quantity': 0.0, 'price': 0.0, 'discount': 0.0,
        #                 'amount': 0.0, 'user': 0, 'cart': 0, 'product': 0, 'warehouse': '0'}

        body_request['id_messenger'] = product_cart_new['id_messenger']
        body_request['quantity'] = float(product_cart_new['quantity'])
        body_request['user'] = user_pk
        body_request['cart'] = cart_pk
        body_request['warehouse'] = product_cart_new['warehouse_pk']
        body_request['product'] = product_cart_new['product_pk']
        product_info = await getProductByPK(session, product_cart_new['product_pk'])
        body_request['price'] = float(product_info.get('price', 0.0))
        body_request['discount_percentage'] = int(
            product_info.get('discount_percentage', 0))

        amount = body_request['price'] * body_request['quantity']
        discount = amount / 100 * body_request['discount_percentage']

        body_request['amount'] = amount - discount
        body_request['discount'] = discount

        exists_product_cart = await getCartProduct(session, cart_pk, product_cart_new['product_pk'], product_cart_new['id_messenger'])

        # если нашли строку в корзине с этим же товаром, пересчитаем количество и сумму, если нет, добавим новую строку
        if exists_product_cart:
            body_request_update = {}
            body_request_update['quantity'] = body_request['quantity'] + float(exists_product_cart['quantity'])

            amount = body_request['price'] * body_request_update['quantity']
            discount = amount / 100 * body_request['discount_percentage']

            body_request_update['amount'] = amount - discount
            body_request_update['discount'] = discount

            async with session.patch(f"{config.ADDR_SERV}/api/v1/carts/product_to_cart_update/{exists_product_cart['pk']}", json=body_request_update):
                pass
        else:
            async with session.post(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart_create', json=body_request):
                pass

        # Теперь изменим общие данные корзины после добавления нового товара
        body_request_cart = {
            'quantity': float(cart_info.get('quantity', 0.0)) + body_request['quantity'],
            'amount': float(cart_info.get('amount', 0.0)) + body_request['amount'],
            'discount': float(cart_info.get('discount', 0.0)) + body_request['discount'],
        }

        async with session.patch(f'{config.ADDR_SERV}/api/v1/carts_update/{cart_pk}', json=body_request_cart):
            pass


# удаляет товар из корзины или заказа, так как строки принадлежат и корзинам и заказам
async def delete_product_from_cart(product_cart_info: dict) -> None:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        user_pk = await getUserByToken(session)
        cart_info = await getCartForUser(session, user_pk)
        cart_pk = cart_info.get('pk', 0)

        # получим pk удаляемой строки
        product_cart = await getCartProduct(session, cart_pk, product_cart_info['product_pk'], product_cart_info['id_messenger'])
        product_cart_pk = product_cart.get('pk', 0)

        async with session.delete(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart_delete/{product_cart_pk}'):
            pass

        # Теперь изменим общие данные корзины или заказа после удаления строки товара
        body_request_cart = {
            'quantity': float(cart_info.get('quantity', 0.0)) - float(product_cart.get('quantity', 0.0)),
            'amount': float(cart_info.get('amount', 0.0)) - float(product_cart.get('amount', 0.0)),
            'discount': float(cart_info.get('discount', 0.0)) - float(product_cart.get('discount', 0.0)),
        }

        async with session.patch(f'{config.ADDR_SERV}/api/v1/carts_update/{cart_pk}', json=body_request_cart):
            pass


# Создает заказ в БД сайта и возвращает обновленную инфу о нем
async def create_order(order_info: dict) -> dict:
    order_info['id'] = 0

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        if not 'status' in order_info:
            order_info['status'] = await getStatus(session)

        if not 'delivery_type' in order_info:
            order_info['delivery_type'] = await getDeliveryType(session)

        if not 'payment_type' in order_info:
            order_info['payment_type'] = await getPaymentType(session)

        user_pk = await getUserByToken(session)
        order_info['user'] = user_pk
        order_info['quantity'] = 0.0
        order_info['discount'] = 0.0
        order_info['amount'] = 0.0
        cart_info = await getCartForUser(session, user_pk)
        cart_pk = cart_info.get('pk', 0)
        products_in_cart = await getCartProducts(session, cart_pk, order_info['id_messenger'])

        for product_cart in products_in_cart:
            order_info['quantity'] += float(product_cart['quantity'])
            order_info['discount'] += float(product_cart['discount'])
            order_info['amount'] += float(product_cart['amount'])

        # Теперь изменю общие данные корзины после удаления строк товара из корзины для заказа
        body_request_cart = {
            'quantity': float(cart_info.get('quantity', 0.0)) - order_info['quantity'],
            'amount': float(cart_info.get('amount', 0.0)) - order_info['amount'],
            'discount': float(cart_info.get('discount', 0.0)) - order_info['discount'],
        }

        async with session.patch(f'{config.ADDR_SERV}/api/v1/carts_update/{cart_pk}', json=body_request_cart):
            pass

        # сначала создаю Заказ и получаю его id, к нему еще не будут привязаны строки заказа, затем делаю обновление строк корзины,
        # куда записываю id заказа, а id корзины ставлю null, получается рокировка заказа с корзиной
        # так строки корзины становятся строками заказа
        async with session.post(f'{config.ADDR_SERV}/api/v1/orders_create', json=order_info) as resp:
            if resp.ok:
                new_order = await resp.json()
                order_info['id'] = new_order.get('id', 0)
                body_request_update = {
                    'order': new_order.get('id', 0),
                    'cart': '',
                    'phone': new_order.get('phone', ''),
                }

                for product_cart in products_in_cart:
                    product_cart_pk = product_cart.get('id', 0)

                    async with session.patch(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart_update/{product_cart_pk}', json=body_request_update):
                        pass

    return order_info


# Добавляет товары из корзины к существующему заказу
async def add_products_from_cart_to_order(order_info: dict) -> dict:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        user_pk = order_info.get('user', 0)
        cart_info = await getCartForUser(session, user_pk)
        cart_pk = cart_info.get('pk', 0)
        id_messenger = order_info.get('id_messenger', 0)
        products_in_cart = await getCartProducts(session, cart_pk, id_messenger)

        order_info['quantity'] = float(order_info['quantity'])
        order_info['discount'] = float(order_info['discount'])
        order_info['amount'] = float(order_info['amount'])

        for product_cart in products_in_cart:
            order_info['quantity'] += float(product_cart['quantity'])
            order_info['discount'] += float(product_cart['discount'])
            order_info['amount'] += float(product_cart['amount'])

         # Изменю общие данные корзины после удаления строк товара из корзины для заказа
        body_request_cart = {
            'quantity': float(cart_info.get('quantity', 0.0)) - order_info['quantity'],
            'amount': float(cart_info.get('amount', 0.0)) - order_info['amount'],
            'discount': float(cart_info.get('discount', 0.0)) - order_info['discount'],
        }

        async with session.patch(f'{config.ADDR_SERV}/api/v1/carts_update/{cart_pk}', json=body_request_cart):
            pass

        # Изменю и сам заказ
        order_pk = order_info.get('id', 0)
        order_info['status'] = 1
        order_info.pop('delivery_type')
        order_info.pop('payment_type')

        async with session.patch(f'{config.ADDR_SERV}/api/v1/orders_update/{order_pk}', json=order_info) as resp:
            if resp.ok:
                body_request_update = {
                    'order': order_pk,
                    'cart': '',
                    'phone': order_info.get('phone', ''),
                }

                for product_cart in products_in_cart:
                    product_cart_pk = product_cart.get('id', 0)

                    async with session.patch(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart_update/{product_cart_pk}', json=body_request_update):
                        pass


    return order_info


# Получу заказы привязанные к id_messenger
async def get_orders_for_messenger(id_messenger: int, paid: int) -> list:
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
        paid_text = 'оплачен' if order['paid'] else 'неоплачен'
        date_order = datetime.strptime(
            order['time_update'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d.%m.%Y')
        text_order = f"Заказ №{order['id']} от {date_order} статус: {paid_text}"
        order_pk = order.get('id', 0)

        new_button = InlineKeyboardButton(
            text=text_order,
            callback_data=f'order_pk{order_pk}'
        )

        kb_orders.add(new_button)

    button_cancel = InlineKeyboardButton(
        text='Отмена', callback_data='cancel'
    )
    kb_orders.add(button_cancel)

    return kb_orders


# возвращает данные о товарах в заказе в виде словаря, где ключом является строка с данными о товаре,
# а значением кнопка действия с этим товаром(например "Удалить") и данные о самом заказе в виде словаря
async def get_order(order_pk: str, paid: int) -> tuple:
    order_info = {}
    order_products = {}

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        params_get = {'pk': order_pk, 'paid': paid}

        async with session.get(f'{config.ADDR_SERV}/api/v1/orders', params=params_get) as resp:
            if resp.ok:
                orders_list = await resp.json()

                if orders_list:
                    order_info = orders_list[0]
                    date_order = datetime.strptime(order_info['time_update'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d.%m.%Y')
                    order_info['order'] = f"<strong>Заказ №{order_info['id']} от {date_order}\n</strong>"
                else:
                    return order_products, order_info

        products_in_order = await getOrderProducts(session, order_pk)

        for product in products_in_order:
            product_info = f"<strong>{product['product']['name']}</strong>\nКоличество: {product['quantity'].split('.')[0]} на сумму: {product['amount']}₽"

            kb_cart = InlineKeyboardMarkup(row_width=2)
            info_button = InlineKeyboardButton(
                text='📦 О товаре',
                callback_data=f"show_product{product['product']['pk']}"
            )
            delete_button = InlineKeyboardButton(
                text='🚽 Удалить',
                callback_data=f"delete_product_from_order{product['product']['pk']}:{order_pk}"
            )

            kb_cart.add(info_button)

            if order_info['status']['repr'] == 'Новый заказ':
                kb_cart.insert(delete_button)

            order_products[product_info] = kb_cart

    return order_products, order_info


# Проверяет достаточно ли товара для отгрузки
# difference_info - словарь Наименование товара:Разница остатков, если пустой, то всего хватает
async def check_stock_in_order(order_pk: str) -> dict:
    difference_info = {}

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        products_in_order = await getOrderProducts(session, order_pk)

        for product_order in products_in_order:
            order_quantity = float(product_order['quantity'])
            warehouse_order = product_order['warehouse']['pk']
            product_stocks = product_order['product']['get_stock_product']

            for product_stock in product_stocks:
                quantity_difference = float(product_stock['stock']) - order_quantity

                if product_stock['warehouse']['pk'] == warehouse_order and quantity_difference < 0:
                    difference_info[product_order['product']['name']] == -quantity_difference

    return difference_info


# удаляет товар из корзины или заказа, так как строки принадлежат и корзинам и заказам
async def delete_product_from_order(product_cart_info: dict) -> None:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        order_pk = product_cart_info['order_pk']
        _, order_info = await get_order(order_pk, 0)

        # получим pk удаляемой строки
        product_order = await getCartProduct(session, order_pk, product_cart_info['product_pk'], product_cart_info['id_messenger'], True)
        product_order_pk = product_order.get('pk', 0)

        async with session.delete(f'{config.ADDR_SERV}/api/v1/carts/product_to_cart_delete/{product_order_pk}'):
            pass

        # Теперь изменим общие данные корзины или заказа после удаления строки товара
        body_request_cart = {
            'quantity': float(order_info.get('quantity', 0.0)) - float(product_order.get('quantity', 0.0)),
            'amount': float(order_info.get('amount', 0.0)) - float(product_order.get('amount', 0.0)),
            'discount': float(order_info.get('discount', 0.0)) - float(product_order.get('discount', 0.0)),
        }

        if float(order_info.get('quantity', 0.0)) == float(product_order.get('quantity', 0.0)):
            # статус Заказ отменен, так как не осталось больше товаров  в заказе
            body_request_cart['status'] = 5

        async with session.patch(f'{config.ADDR_SERV}/api/v1/orders_update/{order_pk}', json=body_request_cart):
            pass


async def set_order_payment(order_pk: str) -> None:
    order_info = {'paid': 1}
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.patch(f'{config.ADDR_SERV}/api/v1/orders_update/{order_pk}', json=order_info):
            pass
