from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, LabeledPrice, PreCheckoutQuery, ContentType
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, Command, state
import config
import services
from main import dp


class FSMOrder(state.StatesGroup):
    ask_about_create_order = state.State()
    input_first_name = state.State()
    input_last_name = state.State()
    input_city = state.State()
    input_street = state.State()
    input_house = state.State()
    input_phone = state.State()
    ask_about_comment = state.State()
    input_comment = state.State()


class FSMAddProductToCart(state.StatesGroup):
    input_code_product = state.State()
    input_quantity = state.State()
    input_warehouse = state.State()


class FSMDeleteProductToCart(state.StatesGroup):
    confirm_delete = state.State()


class FSMDeleteProductFromOrder(state.StatesGroup):
    confirm_delete = state.State()


class FSMPaymentOrder(state.StatesGroup):
    confirm_payment = state.State()


@dp.message_handler(Command(['start', 'help']))
async def start_message(message: Message):
    await message.answer(text='🤖: "Добро пожаловать в Маркет Скидок! Наш магазин работает только на доставку. Приятных покупок."',
                         reply_markup=await services.get_start_menu(message.from_user.id))


@dp.message_handler(Text('📦Товары'))
async def show_products(message: Message):
    kb_categories = await services.get_categories()
    await message.answer('Выберите категорию товара:', reply_markup=kb_categories)


# @dp.message_handler(Text('🛒Корзина'))
@dp.message_handler(lambda msg: '🛒Корзина' in msg.text)
async def show_cart(message: Message):
    cart_info = await services.get_cart(message.from_user.id)

    if cart_info['amount_cart'] == 0:
        await message.answer('Корзина пуста')
        return

    await message.answer('Товары в корзине:')

    for product in cart_info:
        if product != 'amount_cart' and product != 'current_sign':
            await message.answer(product, reply_markup=cart_info[product])

    await message.answer(f"Общая сумма товаров: {cart_info['amount_cart']:10.2f}{cart_info['current_sign']}")


@dp.callback_query_handler(text_contains='cancel')
async def cancel(call: CallbackQuery):
    # await call.answer('Отмена', show_alert=True)
    # await call.message.edit_text('...')
    # await call.message.edit_reply_markup(reply_markup=None)
    await call.message.delete()


@dp.callback_query_handler(lambda cq: 'category_nested_pk' in cq.data)
async def get_subcategory_list(call: CallbackQuery):
    await call.answer(cache_time=60)
    subcategory_pk = call.data.replace('category_nested_pk', '')
    kb_subcategories = await services.get_categories(subcategory_pk)
    await call.message.answer(text='Выберите подкатегорию:', reply_markup=kb_subcategories)


@dp.callback_query_handler(lambda cq: 'category_pk' in cq.data)
async def get_product_list(call: CallbackQuery):
    await call.answer(cache_time=60)
    category_pk = call.data.replace('category_pk', '')
    kb_products = await services.get_product_list(category_pk)
    await call.message.answer(text='Выберите товар:', reply_markup=kb_products)


@dp.callback_query_handler(lambda cq: 'show_product' in cq.data)
async def get_product(call: CallbackQuery):
    await call.answer(cache_time=60)
    product_pk = call.data.replace('show_product', '')
    kb_show_product, info_str, url_photo = await services.get_product_info(product_pk)

    if config.DEBUG_MODE:
        await call.message.answer(text=f'{url_photo}\n{info_str}', reply_markup=kb_show_product)
    else:
        await call.bot.send_photo(call.message.chat.id, url_photo, info_str, reply_markup=kb_show_product)


# Начало диалога добавления товара в Корзину
# **********************************************************************************************************************
# Начнем с кнопки подтверждения выбора, для проброса кода товара в запрос к БД
@dp.callback_query_handler(lambda cq: 'add_product_to_cart' in cq.data, state=None)
async def add_product_to_cart(call: CallbackQuery):
    product_pk = call.data.replace('add_product_to_cart', '')
    await FSMAddProductToCart.input_code_product.set()
    await call.message.answer('Добавить в корзину?', reply_markup=await services.get_confirm_add_product_to_cart(product_pk))


# если нажали "нет", то завершим машинное состояние
@dp.callback_query_handler(lambda cq: 'not_confirm_add_product_to_cart' in cq.data, state=FSMAddProductToCart.input_code_product)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text('Товар не добавлен', reply_markup=None)


@dp.callback_query_handler(lambda cq: 'confirm_add_product_to_cart' in cq.data, state=FSMAddProductToCart.input_code_product)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    product_pk = call.data.replace('confirm_add_product_to_cart', '')

    async with state.proxy() as data:
        data['product_pk'] = product_pk

    await FSMAddProductToCart.next()
    await call.message.answer('Укажите требуемое количество:', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state=FSMAddProductToCart.input_quantity)
async def input_quantity(message: Message, state: FSMContext):
    async with state.proxy() as data:
        if not message.text.isdigit():
            await message.answer('Вы ввели не корректное число. Укажите ещё раз количество:')
            return

        data['quantity'] = message.text
        data['id_messenger'] = message.from_user.id
        product_pk = data['product_pk']

    await FSMAddProductToCart.next()
    await message.answer('Выберите склад из списка:', reply_markup=await services.get_warehouses_kb(product_pk, message.text))


@dp.callback_query_handler(lambda cq: 'warehouse_pk' in cq.data, state=FSMAddProductToCart.input_warehouse)
async def input_warehouse(call: CallbackQuery, state: FSMContext):
    warehouse_pk = call.data.replace('warehouse_pk', '')
    # что бы два раза пользователь не нажимал кнопку и не плодил дубли
    await call.message.delete()

    async with state.proxy() as data:
        data['warehouse_pk'] = warehouse_pk
        # пишем данные в БД корзины и словареподобный объект <class 'aiogram.dispatcher.storage.FSMContextProxy'> легко распаковывается в обычный словарь
        product_cart_new = {**data}
        await services.add_product_to_cart(product_cart_new)
        await call.message.answer('Товар добавлен в корзину', reply_markup=await services.get_start_menu(call.from_user.id))

    await state.finish()


# Конец диалога добавления в корзину
# **************************************************************************************************************


# Начало диалога удаления товара из корзины
# **************************************************************************************************************
@dp.callback_query_handler(lambda cq: 'delete_product_from_cart' in cq.data, state=None)
async def delete_product_from_cart(call: CallbackQuery, state: FSMContext):
    await call.answer(cache_time=60)
    await FSMDeleteProductToCart.confirm_delete.set()
    product_pk = call.data.replace('delete_product_from_cart', '')

    async with state.proxy() as data:
        data['product_pk'] = product_pk

    await call.message.answer('Удалить товар из корзины?', reply_markup=await services.get_answer_yes_no_kb())


# если нажали "нет", то завершим машинное состояние
@dp.callback_query_handler(lambda cq: 'answer_yes_no0' in cq.data, state=FSMDeleteProductToCart.confirm_delete)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.delete()
    await call.message.answer('Товар остался в корзине', reply_markup=await services.get_start_menu(call.from_user.id))


@dp.callback_query_handler(lambda cq: 'answer_yes_no1' in cq.data, state=FSMDeleteProductToCart.confirm_delete)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['id_messenger'] = call.from_user.id
        product_cart_info = {**data}
        await services.delete_product_from_cart(product_cart_info)
        await call.message.answer('Товар удален из корзины', reply_markup=await services.get_start_menu(call.from_user.id))
    
    await state.finish()


# Конец диалога удаления товара из корзины
# **************************************************************************************************************


# Начало диалога оформления Заказа через машинные состояния
# **************************************************************************************************************
@dp.message_handler(Text('🧾Оформить заказ'), state=None)
async def ask_about_create_order(message: Message):
    cart_empty = await services.check_cart(message.from_user.id)

    if cart_empty:
        await message.answer('Ваша корзина пуста, для создания заказа или добавления товара к существующему заказу, нужно добавить в корзину товар.')
        return

    await FSMOrder.ask_about_create_order.set()
    await message.answer('Желаете оформить заказ?', reply_markup=await services.get_answer_yes_no_kb())


@dp.callback_query_handler(lambda cq: 'answer_yes_no' in cq.data, state=FSMOrder.ask_about_create_order)
async def add_product(call: CallbackQuery, state: FSMContext):
    answer = call.data.replace('answer_yes_no', '')

    if answer == '1':
        # если есть неоплаченный заказ в БД, добавлю товар к нему вместо оформления нового заказа
        id_messenger = call.from_user.id
        orders = await services.get_orders_for_messenger(id_messenger, 0)

        if orders:
            order_info = orders[0]
            # order_info['status_pk'] = 1 # статус определит сам бэкенд сайта
            order_info = await services.create_or_update_order(order_info)
            result_check = services.check_before_payment(order_info)
            
            if result_check:
                await call.message.answer(result_check, reply_markup=await services.get_start_menu(call.from_user.id))
                await state.finish()
                return

            await call.message.answer('Ваш существующий заказ обновлён и его можно оплатить.', reply_markup=await services.get_start_menu(call.from_user.id))
            await order_payment(call.message, order_info)
            await state.finish()
            return
            # ****************************************************************************************

        await FSMOrder.next()
        await call.message.answer('Укажите имя:', reply_markup=ReplyKeyboardRemove())
    else:
        await call.message.delete()
        await state.finish()


# Ловим первый ответ пользователя
@dp.message_handler(state=FSMOrder.input_first_name)
async def input_first_name(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['first_name'] = message.text

    await FSMOrder.next()
    await message.answer('Укажите фамилию:', reply_markup=ReplyKeyboardRemove())


# Ловим второй ответ
@dp.message_handler(state=FSMOrder.input_last_name)
async def input_last_name(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['last_name'] = message.text

    await FSMOrder.next()
    await message.answer('Укажите название вашего населённого пункта:', reply_markup=ReplyKeyboardRemove())


# Ловим название города
@dp.message_handler(state=FSMOrder.input_city)
async def input_last_name(message: Message, state: FSMContext):
    async with state.proxy() as data:
        if len(message.text.strip()) < 3:
            await message.answer('Вы ввели слишком короткое название. Укажите верное название вашего населённого пункта:', reply_markup=ReplyKeyboardRemove())
            await state.set_state(FSMOrder.input_city)
            return

        data['address'] = f'Город: {message.text}'

    await FSMOrder.next()
    await message.answer('Укажите название улицы:', reply_markup=ReplyKeyboardRemove())


# Ловим название улицы
@dp.message_handler(state=FSMOrder.input_street)
async def input_last_name(message: Message, state: FSMContext):
    async with state.proxy() as data:
        if len(message.text.strip()) < 5:
            await message.answer('Вы ввели слишком короткое название. Укажите верное название вашей улицы:', reply_markup=ReplyKeyboardRemove())
            await state.set_state(FSMOrder.input_street)
            return

        data['address'] += f', улица: {message.text}'

    await FSMOrder.next()
    await message.answer('Укажите номер дома:', reply_markup=ReplyKeyboardRemove())


# Ловим номер дома
@dp.message_handler(state=FSMOrder.input_house)
async def input_last_name(message: Message, state: FSMContext):
    async with state.proxy() as data:
        if len(message.text.strip()) < 1:
            await message.answer('Вы не указали номер дома. Укажите верный номер вашего дома:', reply_markup=ReplyKeyboardRemove())
            await state.set_state(FSMOrder.input_house)
            return

        data['address'] += f', дом: {message.text}'

    await FSMOrder.next()
    await message.answer('<strong>Отправьте свой номер телефона нажатием на БОЛЬШУЮ кнопку внизу экрана</strong>', reply_markup=await services.get_contact_kb())


# Ловим контактные данные
@dp.message_handler(content_types=['contact'], state=FSMOrder.input_phone)
async def get_contact(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.contact.phone_number
        data['id_messenger'] = message.contact.user_id

    await FSMOrder.next()
    await message.answer('Почти готово!', reply_markup=await services.get_start_menu(message.from_user.id))
    await message.answer('Желаете оставить комментарий к заказу?', reply_markup=await services.get_answer_yes_no_kb())


@dp.callback_query_handler(lambda cq: 'answer_yes_no' in cq.data, state=FSMOrder.ask_about_comment)
async def get_comment(call: CallbackQuery, state: FSMContext):
    answer = call.data.replace('answer_yes_no', '')

    if answer == '1':
        await FSMOrder.next()
        await call.message.answer('Оставьте комментарий:', reply_markup=ReplyKeyboardRemove())
    else:
        async with state.proxy() as data:
            order_info = {**data}
            order_info = await services.create_or_update_order(order_info)
            result_check = services.check_before_payment(order_info)
            
            if result_check:
                await call.message.answer(result_check, reply_markup=await services.get_start_menu(call.from_user.id))
                await state.finish()
                return

            await call.message.answer('Спасибо за Ваш заказ! После оплаты ожидайте звонка от сотрудника магазина.', reply_markup=await services.get_start_menu(call.from_user.id))
            await order_payment(call.message, order_info)

        await state.finish()


async def order_payment(message: Message, order_info: dict) -> None:
    await message.answer('К сожалению в данный момент онлайн оплата не доступна, в будущем мы подключим её. Вы можете оплатить товар курьеру наличными при получении.', reply_markup=await services.get_start_menu(message.from_user.id))
    
    ## Пока что отключим онлайн оплату
    # prices = [LabeledPrice('Руб', int(order_info['amount']) * 100), ]

    # await message.bot.send_invoice(
    #     chat_id=message.chat.id,
    #     title='Заказ',
    #     description='Покупка товаров в магазине',
    #     payload=f"order_pk{order_info['id']}",
    #     provider_token=config.PROVIDER_TOKEN,
    #     currency='RUB',
    #     prices=prices,
    #     start_parameter='test',
    # )


# Проверяет наличие товара на складе для проведения платежа по номеру транзакии pre_checkout_query.id
@dp.pre_checkout_query_handler()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    # если check_info пуст, то все ОК, иначе в словаре будет наименование и расхождение количества
    order_pk = pre_checkout_query.invoice_payload.replace('order_pk', '')
    check_info = await services.check_stock_in_order(order_pk)
    confirm = False if check_info else True
    await pre_checkout_query.bot.answer_pre_checkout_query(pre_checkout_query.id, confirm)


# обработаем принятый платеж
@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def process_pay(message: Message):
    if 'order_pk' in message.successful_payment.invoice_payload:
        # Здесь нужно поменять признак в Заказе на Оплачен
        order_pk = message.successful_payment.invoice_payload.replace('order_pk', '')
        await services.set_order_payment(order_pk)
        await message.answer('Оплата прошла успешно!', reply_markup=await services.get_start_menu())


# Ловим комментарий, если он есть
@dp.message_handler(state=FSMOrder.input_comment)
async def input_comment(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['comment'] = message.text
        order_info = {**data}
        order_info = await services.create_or_update_order(order_info)
        result_check = services.check_before_payment(order_info)
            
        if result_check:
            await message.answer(result_check, reply_markup=await services.get_start_menu())
            await state.finish()
            return
        
        await message.answer('Спасибо за Ваш заказ! После оплаты ожидайте звонка от сотрудника магазина.', reply_markup=await services.get_start_menu())
        await order_payment(message, order_info)

    await state.finish()


# Конец диалога оформления Заказа
# **********************************************************************************************************************


# Показать список неоплаченных заказов покупателя
@dp.message_handler(Text('💼Неоплаченные заказы'))
async def get_order_list(message: Message):
    kb_orders = await services.get_kb_order_list(message.from_user.id, 0)

    # Если заказов не найдено, то в словаре будет всего одна кнопка Отмена
    if len(kb_orders.values['inline_keyboard']) == 1:
        await message.answer('Неоплаченных заказов нет')
        return

    await message.answer('Ваши неоплаченные заказы:', reply_markup=kb_orders)


# Показать список оплаченных заказов покупателя
@dp.message_handler(Text('💼💰Оплаченные заказы'))
async def get_order_list(message: Message):
    kb_orders = await services.get_kb_order_list(message.from_user.id, 1)

    # Если заказов не найдено, то в словаре будет всего одна кнопка "Отмена"
    if len(kb_orders.values['inline_keyboard']) == 1:
        await message.answer('Оплаченных заказов нет')
        return

    await message.answer('Ваши оплаченные заказы:', reply_markup=kb_orders)


# Показать заказ покупателя
@dp.callback_query_handler(lambda cq: 'show_order_pk' in cq.data)
async def get_order(call: CallbackQuery):
    param_list = call.data.replace('show_order_pk', '').split(':')
    order_pk = param_list[0]
    paid = int(param_list[1]) if param_list[1].isdigit() else 0
    order_products_kb, order_info = await services.get_kb_order_info(order_pk, paid)

    if not order_products_kb:
        await call.message.answer('Заказ пуст.')
        return

    order_sum_info = f"{order_info['order_repr']}на сумму {order_info['amount']}{order_info['currency']['sign']}"
    order_status_info = f"Статус заказа: <i>{order_info['status']['name']}</i>"
    order_delivery_info = f"Способ получения: <i>{order_info['delivery_type']['name']}</i>"
    order_type_payment = f"Тип оплаты: <i>{order_info['payment_type']['name']}</i>"
    order_address = f"Адрес доставки: <i>{order_info['address']}</i>"

    if order_info:
        await call.message.answer(
            f"{order_sum_info}\n{order_status_info}\n{order_delivery_info}\n{order_type_payment}\n{order_address}\n<strong>Товары в заказе:</strong>"
        )

    for product in order_products_kb:
        await call.message.answer(product, reply_markup=order_products_kb[product])


# Начало диалога удаления товара из заказа
# **************************************************************************************************************
@dp.callback_query_handler(lambda cq: 'delete_product_from_order' in cq.data, state=None)
async def delete_product_from_cart(call: CallbackQuery, state: FSMContext):
    await call.answer(cache_time=60)
    await FSMDeleteProductFromOrder.confirm_delete.set()
    param_list = call.data.replace('delete_product_from_order', '').split(':')
    product_pk = param_list[0]
    order_pk = param_list[1]

    async with state.proxy() as data:
        data['product_pk'] = product_pk
        data['order_pk'] = order_pk

    await call.message.answer('Удалить товар из заказа?', reply_markup=await services.get_answer_yes_no_kb())


# если нажали "нет", то завершим машинное состояние
@dp.callback_query_handler(lambda cq: 'answer_yes_no0' in cq.data, state=FSMDeleteProductFromOrder.confirm_delete)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.delete()
    await call.message.answer('Товар остался в заказе', reply_markup=await services.get_start_menu(call.from_user.id))


@dp.callback_query_handler(lambda cq: 'answer_yes_no1' in cq.data, state=FSMDeleteProductFromOrder.confirm_delete)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['id_messenger'] = call.from_user.id
        product_cart_info = {**data}
        await services.delete_product_from_cart(product_cart_info)
        await call.message.answer('Товар удален из заказа', reply_markup=await services.get_start_menu(call.from_user.id))

    await state.finish()


# Конец диалога удаления товара из заказа
# **************************************************************************************************************


# Начало диалога оплаты заказа
# **************************************************************************************************************
@dp.callback_query_handler(lambda cq: 'payment_for_order' in cq.data, state=None)
async def start_payment(call: CallbackQuery, state: FSMContext):
    await call.answer(cache_time=60)
    await FSMPaymentOrder.confirm_payment.set()
    param_list = call.data.replace('payment_for_order', '').split(':')
    order_pk = param_list[0]
    order_amount = param_list[1]
    
    async with state.proxy() as data:
        data['id'] = order_pk
        data['amount'] = float(order_amount)
    
    await call.message.answer(f'Оплатить заказ на сумму: {order_amount}?', reply_markup=await services.get_answer_yes_no_kb())


# отказались от оплаты
@dp.callback_query_handler(lambda cq: 'answer_yes_no0' in cq.data, state=FSMPaymentOrder.confirm_payment)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.delete()
    await call.message.answer('Заказ сохранён и позже его можно оплатить или изменить.', reply_markup=await services.get_start_menu(call.from_user.id))


# оплачивают заказ
@dp.callback_query_handler(lambda cq: 'answer_yes_no1' in cq.data, state=FSMPaymentOrder.confirm_payment)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        order_info = {**data}
        await call.message.answer('Спасибо за Ваш заказ! После оплаты ожидайте звонка от сотрудника магазина.', reply_markup=await services.get_start_menu(call.from_user.id))
        await order_payment(call.message, order_info)

    await state.finish()


# Конец диалога оплаты заказа
# **************************************************************************************************************
