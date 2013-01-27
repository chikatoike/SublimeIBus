===========
SublimeIBus
===========

これは `ibus.el <http://www11.atwiki.jp/s-irie/pages/21.html>`_ を Sublime Text 2 に移植したものです。
Sublime Text 2 で iBus を使った日本語入力を可能にするパッケージになる予定です。

注意
====
現在はベータ版未満です。まともに動作しません。

対象となる利用者
================
- Linux の Sublime Text 2 で日本語入力したい人
- `InputHelper <https://github.com/xgenvn/InputHelper>`_ による日本語入力に不満を持っている人
- iBusを利用している人

  SCIM、uim、その他のIMには対応していません。

システム要件
============
以下のソフトウェアがインストールされている必要があります。

- Sublime Text 2 32bit

  64bit版では未確認です。

- SublimeIBus (このパッケージ)

  `インストール方法`_ を参照してください。

- iBus

- Python 2.7

  Python 2.6 以下では未確認です。
  ※ Sublime Text 2 に同梱されている Python 処理系とは別にシステムにインストールされている必要があります。

- Python パッケージ
  - python-ibus
  - python-dbus
  - python-xlib

.. - python-gtk2

Ubuntu 12.10
------------
Ubuntu 12.10 では、 iBus と ibus-anthy がデフォルトでインストールされているので、pythonパッケージに関しては以下のコマンドを実行すれば利用可能になります。 (Mozc等を利用する場合は別途 ibus-mozc 等をインストールする必要があります。)
::

  sudo apt-get install python-xlib

インストール方法
================
現在 Package Control には登録していません。ZIPでダウンロードするか、git clone して、 ~/.config/sublime-text-2/Packages に配置してください。

特徴
====
- できること
- できないこと

  - 半角/全角、無変換、変換、ひらがなキーによる操作はできず、これらのキーに対してキーバインドを設定することはできません。
  - on the stop 方式の入力は未対応です。

未確認事項
==========
現状、以下に挙げた項目は未確認のためよくわかっていません。

- Sublime Text 2 64bit での動作
- Python 2.7 以外での動作
- かな入力の対応

.. 課題
.. ================
.. ここに書いてあることは現在実現できていません。将来的に実装する予定です。
.. - かな入力の対応
.. - タブ毎にIMEの状態を保持
.. - 検索文字列入力欄で、未確定文字列で検索する？

その他のIMに関して
==================
SCIM に関しては、 ScimBridge のクライアント機能を実装すれば対応可能と思われます。
uim に関してはよくわかりません。

参考リンク
==========
http://www.sublimetext.com/forum/viewtopic.php?f=3&t=7006&p=33169
