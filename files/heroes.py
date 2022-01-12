import pygame.mouse
import math

from files.global_stuff import *
from threading import Timer


class BaseHero(BaseGameObject):
    def __init__(self, x, y, image, hp, armor, protection, walk_speed, run_speed, attack_cooldown, damage):
        self.dead = False
        self.max_hp = self.hp = hp
        self.armor = self.max_armor = armor
        self.protection = protection
        self.walk_speed = walk_speed
        self.run_speed = run_speed
        self.attack_cooldown = attack_cooldown
        self.damage = damage
        self.running = False
        self.gun = None
        self.velocity = pygame.Vector2(0, 0)
        super().__init__(x, y, image, [6, 35, 36, 15], PLAYER_TEAM)

    def key_input(self):
        keystates = pygame.key.get_pressed()
        self.velocity.x = self.velocity.y = 0
        if keystates[pygame.K_a]:
            self.velocity.x += -1
        if keystates[pygame.K_d]:
            self.velocity.x += 1
        if keystates[pygame.K_w]:
            self.velocity.y += -1
        if keystates[pygame.K_s]:
            self.velocity.y += 1
        if not self.velocity.is_normalized() and self.velocity.length() != 0:
            self.velocity.normalize_ip()

        if pygame.mouse.get_pressed()[0]:
            self.running = False
            self.attack(*pygame.mouse.get_pos())

    def attack(self, x, y):  # Чтобы ошибка не возникала
        pass

    def update(self):
        self.key_input()
        if self.running:
            move_x, move_y = self.velocity.x * self.run_speed, self.velocity.y * self.run_speed
        else:
            move_x, move_y = self.velocity.x * self.walk_speed, self.velocity.y * self.walk_speed

        self.global_x += move_x
        self.hitbox.set_pos(self.global_x, self.global_y)
        if self.hitbox.get_colliding_objects(include_not_slidable_obj=False):
            self.global_x -= move_x
            self.hitbox.set_pos(self.global_x, self.global_y)

        self.global_y += move_y
        self.hitbox.set_pos(self.global_x, self.global_y)
        if self.hitbox.get_colliding_objects(include_not_slidable_obj=False):
            self.global_y -= move_y
            self.hitbox.set_pos(self.global_x, self.global_y)

        all_sprites.change_layer(self, self.global_y + self.rect.h)
        super().update()

    def take_damage(self, damage):
        damage = damage - self.protection
        if damage > 0:
            self.armor -= damage
            if self.armor < 0:
                self.hp -= abs(self.armor)
                if self.hp <= 0:
                    self.die()
                self.armor = 0

    def change_damage(self, value):
        self.damage = value
        if self.gun:
            self.gun.damage = value

    def die(self):
        self.dead = True


class Spearman(BaseHero):
    def __init__(self, x=0, y=0):
        data = get_hero_characteristic("archer")
        super().__init__(x, y, "abobus.png", *data)
        self.gun = Spear(x, y, self.team, data[-1], self)
        self.spear_dx, self.spear_dy = 30, 5

    def attack(self, x, y):
        if self.gun:
            self.gun.shot()
            self.gun = None
            Timer(self.attack_cooldown, self.new_spear).start()

    def new_spear(self):
        self.gun = Spear(self.global_x, self.global_y, self.team, self.damage, self)
        self.gun.update()


class Spear(BaseGameObject):
    def __init__(self, x, y, team, damage, parent):
        self.damage = damage
        self.parent = parent
        self.angle = 0
        self.speed = 10
        self.shooted = False
        self.vector = pygame.Vector2(0, 0)

        super().__init__(x, y, "arrow.png", hitbox=HITBOX_ARROW, team=team)
        self.orig_image = self.image

    def shot(self):
        self.vector = pygame.Vector2(1, 0).rotate(-self.angle).normalize()
        self.hitbox.mask = pygame.mask.from_surface(self.image)
        self.shooted = True

    def look_at_mouse(self):
        x, y = from_local_to_global_pos(*pygame.mouse.get_pos())
        self.angle = pygame.Vector2(x - self.parent.global_x - self.rect.w // 2, y - self.parent.global_y
                                    - self.rect.h // 2).normalize().angle_to(pygame.Vector2(1, 0))
        if self.angle < 0:
            self.angle += 360
        self.image = pygame.transform.rotate(self.orig_image, self.angle)

    def update(self):
        all_sprites.change_layer(self, self.hitbox.rect.bottom)
        if self.shooted:
            self.global_x += self.vector.x * self.speed
            self.global_y += self.vector.y * self.speed
            for i in self.hitbox.get_colliding_objects():
                if pygame.sprite.collide_mask(self.hitbox, i):
                    if hasattr(i.parent, "hp"):
                        i.parent.take_damage(self.damage)
                    self.die()
        else:
            self.look_at_mouse()
            self.set_pos(self.parent.global_x + 40 * math.cos(self.angle / 180 * math.pi) + 3,
                         self.parent.global_y - 40 * math.sin(self.angle / 180 * math.pi) + 15)

        self.hitbox.set_pos(self.global_x, self.global_y)
        super().update()


class MagicMan(BaseHero):
    def __init__(self, x=0, y=0):
        data = get_hero_characteristic("archer")
        self.can_shot = True
        self.attack_range = 300
        super().__init__(x, y, "abobus.png", *data)

    def attack(self, x, y):
        if self.can_shot:
            x, y = from_local_to_global_pos(x, y)
            vector = pygame.Vector2(x - self.global_x, y - self.global_y)
            if vector.length() >= self.attack_range:
                vector = vector.normalize() * self.attack_range + (self.global_x, self.global_y)
                x, y = vector.x, vector.y
            fire = FireBall(x, y, self.damage, self.team)
            self.can_shot = False
            Timer(self.attack_cooldown, self.enable_shot).start()
            Timer(self.attack_cooldown, fire.die).start()

    def enable_shot(self):
        self.can_shot = True


class FireBall(BaseGameObject):
    def __init__(self, x, y, damage, team):
        self.damage = damage
        self.damage_taken = []
        super().__init__(x - 50, y - 20, "fire.png", HITBOX_FULL_RECT, team)
        all_sprites.change_layer(self, 0)

    def update(self):
        for i in self.hitbox.get_colliding_objects():
            if i in self.damage_taken:
                continue
            if hasattr(i.parent, "hp"):
                i.parent.take_damage(self.damage)
            self.damage_taken.append(i)
        super().update()


class SwordMan(BaseHero):
    def __init__(self, x=0, y=0):
        data = get_hero_characteristic("archer")
        self.can_attack = True
        self.dash_length = 30
        super().__init__(x, y, "abobus.png", *data)
        self.damage = data[-1]
        self.gun = Sword(x, y, self.damage, self.team, self)

    def enable_attack(self):
        self.can_attack = True

    def attack(self, x, y):
        if self.can_attack:
            self.gun.attack()
            self.can_attack = False
            Timer(1, self.enable_attack).start()


class Sword(BaseGameObject):
    def __init__(self, x, y, damage, team, parent):
        self.damage = damage
        self.parent = parent
        self.damage_taken = []
        self.attacking = False
        self.angle = 0
        self.vector = pygame.Vector2(0, 0)
        super().__init__(x - 50, y - 20, "sword.png", HITBOX_ARROW, team)
        self.orig_image = self.image
        all_sprites.change_layer(self, 0)

    def look_at_mouse(self):
        x, y = from_local_to_global_pos(*pygame.mouse.get_pos())
        self.angle = pygame.Vector2(x - self.parent.global_x - self.rect.w // 2, y - self.parent.global_y
                                    - self.rect.h // 2).normalize().angle_to(pygame.Vector2(1, 0))
        if self.angle < 0:
            self.angle += 360
        self.image = pygame.transform.rotate(self.orig_image, self.angle)

    def attack(self):
        self.vector = pygame.Vector2(1, 0).rotate(-self.angle).normalize()
        self.attacking = True
        Timer(0.05, self.attacking_false).start()

    def attacking_false(self):
        self.attacking = False
        self.damage_taken.clear()
        self.vector = pygame.Vector2(0, 0)

    def update(self):
        all_sprites.change_layer(self, self.hitbox.rect.bottom)
        if self.attacking:

            self.global_x += self.vector.x * 10
            self.global_y += self.vector.y * 10
            for i in self.hitbox.get_colliding_objects():
                if i not in self.damage_taken:
                    if pygame.sprite.collide_mask(self.hitbox, i):
                        if hasattr(i.parent, "hp"):
                            i.parent.take_damage(self.damage)
                        self.damage_taken.append(i)
        else:
            self.look_at_mouse()
            self.set_pos(self.parent.global_x + 40 * math.cos(self.angle / 180 * math.pi) + 3,
                         self.parent.global_y - 40 * math.sin(self.angle / 180 * math.pi) + 20)
        self.hitbox.set_pos(self.global_x, self.global_y)
        super().update()
