"""
Management command to seed the database with initial data.
Creates real sample users, files, and transfers for testing.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear  # Clear existing data first
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with sample data for development/testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        from files.models import File, FileChunk
        from transfers.models import Transfer, TransferLog
        
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            TransferLog.objects.all().delete()
            Transfer.objects.all().delete()
            FileChunk.objects.all().delete()
            File.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('Data cleared.'))
        
        self.stdout.write('Creating sample users...')
        users = self._create_users()
        
        self.stdout.write('Creating sample files...')
        files = self._create_files(users)
        
        self.stdout.write('Creating sample transfers...')
        transfers = self._create_transfers(users, files)
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSeeding complete!\n'
            f'  Users created: {len(users)}\n'
            f'  Files created: {len(files)}\n'
            f'  Transfers created: {len(transfers)}\n'
            f'\nSample login credentials:\n'
            f'  Username: alice / Password: password123\n'
            f'  Username: bob / Password: password123\n'
            f'  Username: charlie / Password: password123'
        ))

    def _create_users(self):
        """Create sample users."""
        users_data = [
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'password': 'password123',
                'first_name': 'Alice',
                'last_name': 'Johnson',
                'is_online': True,
            },
            {
                'username': 'bob',
                'email': 'bob@example.com',
                'password': 'password123',
                'first_name': 'Bob',
                'last_name': 'Smith',
                'is_online': True,
            },
            {
                'username': 'charlie',
                'email': 'charlie@example.com',
                'password': 'password123',
                'first_name': 'Charlie',
                'last_name': 'Brown',
                'is_online': False,
            },
            {
                'username': 'diana',
                'email': 'diana@example.com',
                'password': 'password123',
                'first_name': 'Diana',
                'last_name': 'Ross',
                'is_online': True,
            },
            {
                'username': 'evan',
                'email': 'evan@example.com',
                'password': 'password123',
                'first_name': 'Evan',
                'last_name': 'Williams',
                'is_online': False,
            },
        ]
        
        users = []
        for data in users_data:
            password = data.pop('password')
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults=data
            )
            if created:
                user.set_password(password)
                user.last_activity = timezone.now() - timedelta(
                    minutes=random.randint(1, 60)
                )
                user.save()
            users.append(user)
        
        return users

    def _create_files(self, users):
        """Create sample files for users."""
        from files.models import File
        import hashlib
        
        files_data = [
            {
                'original_name': 'project_report.pdf',
                'size': 2457600,  # ~2.4 MB
                'mime_type': 'application/pdf',
            },
            {
                'original_name': 'presentation.pptx',
                'size': 5242880,  # 5 MB
                'mime_type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            },
            {
                'original_name': 'data_backup.zip',
                'size': 104857600,  # 100 MB
                'mime_type': 'application/zip',
            },
            {
                'original_name': 'meeting_notes.docx',
                'size': 524288,  # 512 KB
                'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            },
            {
                'original_name': 'budget_2026.xlsx',
                'size': 1048576,  # 1 MB
                'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            },
            {
                'original_name': 'product_image.png',
                'size': 3145728,  # 3 MB
                'mime_type': 'image/png',
            },
            {
                'original_name': 'demo_video.mp4',
                'size': 52428800,  # 50 MB
                'mime_type': 'video/mp4',
            },
            {
                'original_name': 'source_code.tar.gz',
                'size': 15728640,  # 15 MB
                'mime_type': 'application/gzip',
            },
        ]
        
        files = []
        for i, data in enumerate(files_data):
            owner = users[i % len(users)]
            checksum = hashlib.sha256(
                f"{data['original_name']}{data['size']}".encode()
            ).hexdigest()
            
            file_obj, created = File.objects.get_or_create(
                original_name=data['original_name'],
                owner=owner,
                defaults={
                    'name': data['original_name'],
                    'size': data['size'],
                    'mime_type': data['mime_type'],
                    'checksum': checksum,
                    'is_encrypted': True,
                    'encryption_algorithm': 'AES-256-GCM',
                }
            )
            files.append(file_obj)
        
        return files

    def _create_transfers(self, users, files):
        """Create sample transfers between users."""
        from transfers.models import Transfer, TransferLog
        
        transfers_data = [
            # Completed transfers
            {
                'sender': users[0],  # Alice
                'receiver': users[1],  # Bob
                'file': files[0],
                'status': 'completed',
                'progress': 100,
            },
            {
                'sender': users[1],  # Bob
                'receiver': users[0],  # Alice
                'file': files[1],
                'status': 'completed',
                'progress': 100,
            },
            # Active transfer
            {
                'sender': users[0],  # Alice
                'receiver': users[2],  # Charlie
                'file': files[2],
                'status': 'transferring',
                'progress': 45,
            },
            # Pending transfers
            {
                'sender': users[3],  # Diana
                'receiver': users[0],  # Alice
                'file': files[3],
                'status': 'pending',
                'progress': 0,
            },
            {
                'sender': users[2],  # Charlie
                'receiver': users[1],  # Bob
                'file': files[4],
                'status': 'pending',
                'progress': 0,
            },
            # Failed transfer
            {
                'sender': users[1],  # Bob
                'receiver': users[3],  # Diana
                'file': files[5],
                'status': 'failed',
                'progress': 23,
                'error_message': 'Connection lost during transfer',
            },
            # Key exchange in progress
            {
                'sender': users[4],  # Evan
                'receiver': users[0],  # Alice
                'file': files[6],
                'status': 'key_exchange',
                'progress': 0,
            },
        ]
        
        transfers = []
        for data in transfers_data:
            transfer, created = Transfer.objects.get_or_create(
                sender=data['sender'],
                receiver=data['receiver'],
                file=data['file'],
                defaults={
                    'status': data['status'],
                    'progress': data['progress'],
                    'bytes_transferred': int(
                        data['file'].size * data['progress'] / 100
                    ),
                    'error_message': data.get('error_message'),
                }
            )
            
            if created:
                # Set timestamps based on status
                if data['status'] in ['transferring', 'completed', 'failed']:
                    transfer.started_at = timezone.now() - timedelta(
                        minutes=random.randint(5, 30)
                    )
                
                if data['status'] == 'completed':
                    transfer.completed_at = transfer.started_at + timedelta(
                        seconds=random.randint(60, 300)
                    )
                    transfer.transfer_speed = (
                        transfer.file.size / 
                        (transfer.completed_at - transfer.started_at).total_seconds()
                    )
                
                transfer.save()
                
                # Create log entries
                TransferLog.objects.create(
                    transfer=transfer,
                    event='created',
                    message=f"Transfer initiated by {transfer.sender.username}"
                )
                
                if data['status'] != 'pending':
                    TransferLog.objects.create(
                        transfer=transfer,
                        event='status_changed',
                        old_status='pending',
                        new_status=data['status'],
                        message=f"Status changed to {data['status']}"
                    )
            
            transfers.append(transfer)
        
        return transfers
