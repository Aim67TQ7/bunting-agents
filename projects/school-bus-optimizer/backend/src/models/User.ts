import {
  Table,
  Column,
  Model,
  DataType,
  PrimaryKey,
  Default,
  ForeignKey,
  BelongsTo,
  BeforeCreate,
  BeforeUpdate,
  CreatedAt,
  UpdatedAt
} from 'sequelize-typescript';
import bcrypt from 'bcryptjs';
import { District } from './District';

@Table({
  tableName: 'users',
  timestamps: true,
  indexes: [
    {
      fields: ['email'],
      unique: true
    },
    {
      fields: ['district_id']
    }
  ]
})
export class User extends Model {
  @PrimaryKey
  @Default(DataType.UUIDV4)
  @Column(DataType.UUID)
  id!: string;

  @ForeignKey(() => District)
  @Column({
    type: DataType.UUID,
    allowNull: false
  })
  districtId!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false,
    unique: true
  })
  email!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  password!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  firstName!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  lastName!: string;

  @Column({
    type: DataType.ENUM('admin', 'district_admin', 'driver', 'parent'),
    allowNull: false
  })
  role!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  phone!: string;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: true
  })
  active!: boolean;

  @Column({
    type: DataType.DATE,
    allowNull: true
  })
  lastLoginAt!: Date;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  resetPasswordToken!: string;

  @Column({
    type: DataType.DATE,
    allowNull: true
  })
  resetPasswordExpires!: Date;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: false
  })
  emailVerified!: boolean;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  emailVerificationToken!: string;

  @Column({
    type: DataType.JSON,
    defaultValue: {
      emailNotifications: true,
      smsNotifications: true,
      pushNotifications: true
    }
  })
  preferences!: any;

  @CreatedAt
  createdAt!: Date;

  @UpdatedAt
  updatedAt!: Date;

  // Associations
  @BelongsTo(() => District)
  district!: District;

  // Virtual fields
  get fullName(): string {
    return `${this.firstName} ${this.lastName}`;
  }

  // Instance methods
  async comparePassword(candidatePassword: string): Promise<boolean> {
    return bcrypt.compare(candidatePassword, this.password);
  }

  // Hooks
  @BeforeCreate
  @BeforeUpdate
  static async hashPassword(instance: User) {
    if (instance.changed('password')) {
      const salt = await bcrypt.genSalt(10);
      instance.password = await bcrypt.hash(instance.password, salt);
    }
  }
}